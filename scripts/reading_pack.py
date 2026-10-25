"""Build the reading pack: what André reads outside the repository.

The files are written to ``outputs/leitura`` and, with ``--to``, copied to another
folder (for example the project folder on Google Drive):

    00 Comece aqui.pdf                 what is in the folder and what is needed back
    01 Caderno de casos.pdf            the textbook cases, one per page, with diagrams
    02 Especificação.pdf               the specification
    03 Casos interativos.html          the case gallery, to open in a browser
    04 Ficha de teoria - telecom.pdf   the theory card, for André to correct and approve
    05 Caderno de mundos.pdf           twenty generated worlds, with their numbers
    06 Mundos interativos.html         the same worlds, to open in a browser
    07 Trabalhos vizinhos.pdf          the literature scan (when docs/ has it)
    08 Status do projeto.pdf           what has been done so far (when docs/ has it)

The diagrams of the booklets are taken from the interactive pages themselves, opened in
a headless browser, so the booklets show exactly what the pages show. The browser also
prints the PDFs. Neither is a dependency of the project:

    uv run --with playwright python -m playwright install chromium-headless-shell   # once
    uv run --with playwright --with markdown-it-py python scripts/reading_pack.py \
        --to ~/causalista-leitura
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import shutil
from importlib import resources
from pathlib import Path

from markdown_it import MarkdownIt
from playwright.sync_api import Page, sync_playwright

from causalista.verifier.textbook import load_textbook_cases
from causalista.viz.gallery import gallery_payload, render, render_page
from causalista.viz.worlds_page import worlds_payload, worlds_text
from causalista.worlds import Theory, load_theory
from causalista.worlds.mechanism import ROWS, STRENGTH
from causalista.worlds.theory import LINKS_OF_ROLE, SCALE_KEY, THEORIES_DIR, Role
from causalista.written_cases import load_written_cases

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "leitura"
MARGIN = {"top": "16mm", "bottom": "18mm", "left": "16mm", "right": "16mm"}

# Runs inside the interactive page: puts it in a given state and returns what it shows.
HARVEST = """
({caseId, picks, reveal, neutral, all}) => {
  document.querySelector(`.case-link[data-case="${caseId}"]`).click();
  for (const name of picks) document.querySelector(`.chip[data-name="${name}"]`).click();
  if (all) document.getElementById('pick-all').click();
  if (reveal) document.getElementById('reveal').click();
  const drawing = document.getElementById('graph').cloneNode(true);
  for (const attribute of ['id', 'style', 'role', 'aria-label']) drawing.removeAttribute(attribute);
  drawing.setAttribute('class', 'drawing');
  drawing.querySelectorAll('title').forEach(node => node.remove());
  drawing.querySelectorAll('.node').forEach(node => {
    for (const attribute of ['tabindex', 'role', 'aria-pressed', 'aria-label']) node.removeAttribute(attribute);
  });
  if (neutral) {
    drawing.querySelectorAll('.on').forEach(node => node.classList.remove('on'));
    drawing.querySelectorAll('.on-open').forEach(node => node.classList.remove('on-open'));
  }
  const block = id => {
    const node = document.getElementById(id);
    if (!node || node.hidden) return '';
    const copy = node.cloneNode(true);
    copy.removeAttribute('id');
    copy.querySelectorAll('[id]').forEach(part => part.removeAttribute('id'));
    copy.querySelectorAll('[aria-labelledby]').forEach(part => part.removeAttribute('aria-labelledby'));
    copy.removeAttribute('aria-labelledby');
    return copy.outerHTML;
  };
  return {
    svg: drawing.outerHTML,
    caption: document.getElementById('caption').textContent,
    valid: document.getElementById('verdict-title').textContent === 'Efeito certo',
    verdict: document.getElementById('verdict-body').innerHTML,
    answer: document.getElementById('answer-text').innerHTML,
    numbers: block('numbers'),
    columns: block('columns'),
  };
}
"""

PRINT_STYLE = """
/* Paper: white ground, one column, and the light palette whatever the system theme. */
:root { --bg: #FFFFFF; }
html { font-size: 15px; }
body { background: #FFFFFF; }
.page { max-width: none; padding: 0; }
.doc { display: block; }
.doc h1 { font-size: 2.1rem; }
.doc h2 { font-size: 1.45rem; }
.doc h3 { margin-top: 18px; }
.keep > h3:first-child, .numbers h3 { margin-top: 0; }
/* Plain blocks, not flex columns: page breaks are only reliable in block layout. */
.sheet { break-before: page; display: block; }
.sheet > * + * { margin-top: 12px; }
.keep { break-inside: avoid; }
.keep > * + * { margin-top: 10px; }
.sheet > p, .intro > p { max-width: 42rem; }
.intro { display: block; }
.intro > * + * { margin-top: 11px; }
.toc { break-before: page; }
.toc > * + * { margin-top: 8px; }
.intro ul.plain { display: flex; flex-direction: column; gap: 6px; padding-left: 1.1rem; list-style: disc; max-width: 42rem; }
.intro ol { margin: 0; padding-left: 1.4rem; columns: 2; column-gap: 28px; font-size: 0.9rem; }
.intro ol li { break-inside: avoid; padding-block: 1px; }
.intro .toc-group { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase; color: var(--ink-2); margin-top: 6px; }
.facts { font-size: 0.9rem; color: var(--ink-2); }
.figure { border: 1px solid var(--line-soft); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; break-inside: avoid; }
.figure figcaption { font-size: 0.875rem; }
.drawing { display: block; max-width: 100%; height: auto; margin-inline: auto; }
.answer, .wrong-choice, .review { break-inside: avoid; }
.wrong-choice { border: 1.5px solid var(--bad); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }
.wrong-title { font-weight: 700; color: var(--bad); }
.wrong-choice ul { display: flex; flex-direction: column; gap: 5px; }
.wrong-choice .path { cursor: auto; }
.review { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 22px; margin-top: 4px; padding-top: 10px; border-top: 1px solid var(--line-soft); font-size: 0.9rem; }
.review .tick { display: inline-flex; align-items: center; gap: 7px; }
.review .box { width: 12px; height: 12px; border: 1.4px solid var(--ink); border-radius: 2px; display: inline-block; }
.review .notes { flex: 1 1 100%; border-bottom: 1px solid var(--line); height: 26px; color: var(--ink-2); }
.legend { font-size: 0.875rem; }
.numbers { break-inside: avoid; padding: 12px 14px; }
.columns { break-inside: avoid; }
.columns table { font-size: 0.875rem; }
.sign { font-family: var(--font-mono); font-weight: 600; }

/* Running text set from Markdown (specification and guide). */
.prose { display: block; max-width: none; }
.prose h1 { margin-bottom: 8px; }
.prose h2 { margin-top: 24px; margin-bottom: 8px; break-after: avoid; }
.prose h3 { margin-top: 20px; margin-bottom: 6px; break-after: avoid; font-size: 1.05rem; font-weight: 700; letter-spacing: 0; text-transform: none; color: var(--ink); }
.prose p { margin-block: 8px; max-width: 44rem; }
.prose ul, .prose ol { margin-block: 8px; padding-left: 1.3rem; list-style: revert; max-width: 44rem; }
.prose li { margin-block: 3px; }
.prose table { border-collapse: collapse; margin-block: 12px; font-size: 0.875rem; width: 100%; }
.prose th, .prose td { border: 1px solid var(--line); padding: 5px 8px; text-align: left; vertical-align: top; }
.prose th { background: var(--effect-tint); font-weight: 600; }
.prose tr { break-inside: avoid; }
.prose a { color: var(--effect); overflow-wrap: anywhere; }
.prose code { overflow-wrap: anywhere; }
"""


def _template_parts() -> tuple[str, str, str]:
    """The fonts, the style and the legend of the interactive page, to reuse on paper."""
    template = resources.files("causalista.viz").joinpath("gallery.html").read_text(encoding="utf-8")
    fonts = "\n".join(re.findall(r'<link rel="stylesheet"[^>]*>', template))
    style = re.search(r"<style>(.*?)</style>", template, re.DOTALL).group(1)
    legend = re.search(r'<ul class="legend">.*?</ul>', template, re.DOTALL).group(0)
    return fonts, style, legend


def _document(title: str, body: str) -> str:
    fonts, style, _ = _template_parts()
    return (
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n{fonts}\n"
        f"<style>{style}\n{PRINT_STYLE}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def _names(names: list[str]) -> str:
    """ "a", "a e b", "a, b e c", each name in monospace."""
    coded = [f"<code>{html.escape(name)}</code>" for name in names]
    if len(coded) < 2:
        return "".join(coded)
    return ", ".join(coded[:-1]) + " e " + coded[-1]


def _static(markup: str) -> str:
    """Paths are buttons on the page; on paper they are plain labels."""
    markup = re.sub(r'<button\b[^>]*class="path"[^>]*>', '<span class="path">', markup)
    return markup.replace("</button>", "</span>")


def _case_sheet(page: Page, case: dict, number: int, total: int) -> str:
    def harvest(picks: list[str], *, reveal: bool = False, neutral: bool = False) -> dict:
        return page.evaluate(
            HARVEST, {"caseId": case["id"], "picks": picks, "reveal": reveal, "neutral": neutral}
        )

    answer = case["answer"]
    hidden = sorted(node["name"] for node in case["nodes"] if node["hidden"])
    valid = sorted(
        ([name for name in key.split(",") if name] for key, v in case["verdicts"].items() if v["valid"]),
        key=lambda names: (len(names), names),
    )

    parts = [
        '<section class="sheet">',
        f'<p class="eyebrow">{html.escape(case["group"])} · caso {number} de {total}</p>',
        f"<h2>{html.escape(case['title'])}</h2>",
        f"<p>{html.escape(case['story'])}</p>",
    ]
    if case["note"]:
        parts.append(f'<p class="note">{html.escape(case["note"])}</p>')
    parts.append(
        f'<p class="question">Qual o efeito de <code>{html.escape(case["treatment"])}</code> '
        f'sobre <code>{html.escape(case["outcome"])}</code>?</p>'
    )
    table = (
        f"Outras colunas da tabela: {_names(case['columns'])}."
        if case["columns"]
        else "A tabela não tem outras colunas."
    )
    if hidden:
        table += f" Fora da tabela: {_names(hidden)}."
    parts.append(f'<p class="facts">{table}</p>')

    if answer["identifiable"]:
        shown = harvest([], reveal=True)
        caption = shown["caption"]
    else:
        shown = harvest([], reveal=True, neutral=True)
        caption = "O mundo deste caso. Nenhuma escolha de colunas fecha todos os caminhos não causais."
    parts.append(
        f'<figure class="figure">{shown["svg"]}<figcaption>{html.escape(caption)}</figcaption></figure>'
    )
    parts.append(f'<div class="answer"><strong>Resposta</strong><p>{shown["answer"]}</p></div>')
    if len(valid) > 1:
        listed = "; ".join(_names(names) if names else "nada" for names in valid[:8])
        more = "" if len(valid) <= 8 else f"; e outras {len(valid) - 8}"
        parts.append(f'<p class="facts">Todas as escolhas válidas: {listed}{more}.</p>')

    if case["why"]:
        heading = "<h3>Escolhas tentadoras que dão o efeito errado</h3>"
        for position, key in enumerate(case["why"]):
            picks = [name for name in key.split(",") if name]
            wrong = harvest(picks)
            title = f"Ajustar por {_names(picks)}" if picks else "Não ajustar por nada"
            block = (
                f'<div class="wrong-choice"><p class="wrong-title">{title}</p>'
                f"{_static(wrong['verdict'])}{wrong['svg']}</div>"
            )
            # The heading travels with the first block, so it is never left alone on a page.
            parts.append(f'<div class="keep">{heading}{block}</div>' if position == 0 else block)
    elif all(verdict["valid"] for verdict in case["verdicts"].values()):
        parts.append('<p class="facts">Neste caso, qualquer escolha de colunas dá o efeito certo.</p>')

    parts.append(_review("Concordo", "Discordo", "Não entendi"))
    parts.append("</section>")
    return "\n".join(parts)


def _booklet(page: Page, payload: dict, today: str) -> str:
    _, _, legend = _template_parts()
    cases = payload["cases"]
    reference = json.loads(
        (ROOT / "tests/verifier/reference/dagitty_reference.json").read_text(encoding="utf-8")
    )
    verdicts = f"{sum(len(problem['sets']) for problem in reference['problems']):,}".replace(",", ".")

    toc = []
    for group in payload["groups"]:
        toc.append(f'<p class="toc-group">{html.escape(group)}</p>')
        first = next(i for i, case in enumerate(cases, 1) if case["group"] == group)
        items = "".join(
            f"<li>{html.escape(case['title'])}</li>" for case in cases if case["group"] == group
        )
        toc.append(f'<ol start="{first}">{items}</ol>')

    intro = f"""
<section class="intro">
  <p class="eyebrow">Causalista · fase 1 · {today}</p>
  <h1>Caderno de casos</h1>
  <p class="lede">{len(cases)} mundos pequenos em que a resposta certa é conhecida. São a primeira prova do verificador, a peça que dá o gabarito de todo o projeto.</p>

  <h3>O que preciso de você</h3>
  <p>Leia cada caso e marque: concordo, discordo ou não entendi. Depois me diga os números dos casos em que você discorda ou tem dúvida. Se um caso estiver errado, o erro está no caso ou no verificador, e precisa ser resolvido antes da fase 2.</p>

  <h3>Como ler um caso</h3>
  <p>Cada caso conta uma história, mostra o diagrama de quem causa quem e pergunta qual o efeito da intervenção sobre o resultado. Ajustar por uma coluna é comparar apenas clientes iguais nessa coluna.</p>
  {legend}
  <ul class="plain">
    <li>O caminho causal é o efeito que se quer medir. Ele precisa ficar livre.</li>
    <li>Um caminho não causal aberto é uma ligação entre a intervenção e o resultado que não é efeito da intervenção. Enquanto ele estiver aberto, a comparação sai distorcida.</li>
    <li>Uma escolha é válida quando fecha todos os caminhos não causais sem mexer no caminho causal. Uma escolha válida pode conter uma coluna inútil.</li>
    <li>Quando nenhuma escolha de colunas da tabela é válida, a resposta certa é "não identificável".</li>
  </ul>

  <h3>Como as respostas foram conferidas</h3>
  <ul class="plain">
    <li>As respostas deste caderno foram escritas à mão e batem com as do verificador.</li>
    <li>Em todos os 29.281 grafos de cinco variáveis, dois programas independentes e uma conta de regressão em modelos lineares deram a mesma resposta para todas as escolhas.</li>
    <li>Em {len(reference["problems"])} problemas sorteados ({verdicts} veredictos), o verificador concordou com o dagitty, a implementação de referência.</li>
    <li>Erros plantados de propósito no verificador são pegos pelos testes.</li>
  </ul>

  <div class="toc">
    <h3>Os casos</h3>
    {"".join(toc)}
  </div>
</section>
"""

    sheets = [_case_sheet(page, case, number, len(cases)) for number, case in enumerate(cases, 1)]
    body = f'<div class="page doc" lang="pt-BR">{intro}{"".join(sheets)}</div>'
    return _document("Caderno de casos do Causalista", body)


def _review(*options: str) -> str:
    ticks = "".join(f'<span class="tick"><span class="box"></span>{option}</span>' for option in options)
    return f'<div class="review">{ticks}<span class="notes">Anotações</span></div>'


def _world_sheet(page: Page, world: dict) -> str:
    def harvest(**state) -> dict:
        request = {"caseId": world["id"], "picks": [], "reveal": False, "neutral": False, "all": False}
        return page.evaluate(HARVEST, request | state)

    answer = world["answer"]
    everything = harvest(all=True)
    parts = [
        '<section class="sheet">',
        f'<p class="eyebrow">{html.escape(world["group"])} · {html.escape(world["title"]).lower()}</p>',
        f"<h2>{html.escape(world['title'])}</h2>",
        f"<p>{html.escape(world['story'])}</p>",
        (
            f'<p class="question">Qual o efeito de <code>{html.escape(world["treatment"])}</code> '
            f'sobre <code>{html.escape(world["outcome"])}</code>?</p>'
        ),
        (
            f'<p class="facts">Mundo gêmeo: {html.escape(world["twin"]["title"])}. '
            f'{html.escape(world["twin"]["difference"])}</p>'
        ),
        everything["columns"],
    ]

    if answer["identifiable"]:
        right = harvest(reveal=True)
        parts.append(
            f'<figure class="figure">{right["svg"]}'
            f'<figcaption>{html.escape(right["caption"])}</figcaption></figure>'
        )
        parts.append(f'<div class="answer"><strong>Resposta</strong><p>{right["answer"]}</p></div>')
        parts.append(right["numbers"].replace("Com a sua escolha", "Com o ajuste certo"))
        if everything["valid"]:
            parts.append(
                '<p class="facts">Neste mundo, ajustar por todas as colunas também dá o efeito certo.</p>'
            )
        else:
            block = (
                '<div class="wrong-choice"><p class="wrong-title">Ajustar por todas as colunas</p>'
                f"{_static(everything['verdict'])}{everything['svg']}</div>"
            )
            parts.append(
                '<div class="keep"><h3>O que acontece ao ajustar por tudo</h3>' + block + "</div>"
            )
            parts.append(everything["numbers"].replace("Com a sua escolha", "Ajustando por tudo"))
    else:
        plain = harvest(reveal=True, neutral=True)
        parts.append(
            f'<figure class="figure">{plain["svg"]}<figcaption>O mundo deste caso. Nenhuma escolha '
            "de colunas fecha todos os caminhos não causais.</figcaption></figure>"
        )
        parts.append(f'<div class="answer"><strong>Resposta</strong><p>{plain["answer"]}</p></div>')
        parts.append(everything["numbers"].replace("Com a sua escolha", "Ajustando por tudo"))

    parts.append(_review("Plausível", "Estranho", "Não entendi"))
    parts.append("</section>")
    return "\n".join(parts)


def _gate_numbers() -> str:
    """One sentence with the measured gate of the estimator, when the measurement exists."""
    report = ROOT / "outputs" / "gates" / "estimator_telecom_boosting.json"
    if not report.exists():
        return "A medição do estimador ainda não foi feita (scripts/check_estimator.py)."
    summary = json.loads(report.read_text(encoding="utf-8"))["summary"]

    def percent(value: float) -> str:
        return f"{100 * value:.1f}".replace(".", ",") + "%"

    return (
        f"Em {summary['worlds']} mundos identificáveis, o intervalo calculado com o ajuste certo "
        f"conteve o efeito verdadeiro em {percent(summary['coverage'])} das vezes (o esperado é "
        f"95%). Nos {summary['worlds_with_confounder']} mundos com confundidor, a comparação "
        f"simples só conteve o efeito verdadeiro em {percent(summary['naive_coverage_with_confounder'])}."
    )


def _world_booklet(page: Page, payload: dict, today: str) -> str:
    worlds = payload["cases"]
    _, _, legend = _template_parts()
    missed = []
    for world in worlds:
        if world["answer"]["identifiable"]:
            right = world["numbers"]["estimates"][",".join(world["answer"]["smallest"])]
            if not right["low"] <= world["numbers"]["truth"] <= right["high"]:
                missed.append(world["title"].lower())
    if missed:
        misses = (
            "Um intervalo de 95% deixa o efeito verdadeiro de fora uma vez em vinte, mesmo com o "
            f"ajuste certo. Neste caderno isso acontece em: {', '.join(missed)}."
        )
    else:
        misses = (
            "Um intervalo de 95% deixa o efeito verdadeiro de fora uma vez em vinte, mesmo com o "
            "ajuste certo. Neste caderno isso não chegou a acontecer."
        )
    intro = f"""
<section class="intro">
  <p class="eyebrow">Causalista · fase 2 · {today}</p>
  <h1>Caderno de mundos</h1>
  <p class="lede">{len(worlds)} mundos gerados a partir da ficha de teoria do tema telecom, em {len(worlds) // 2} pares de gêmeos. Cada mundo tem uma história, uma tabela e uma resposta certa conhecida.</p>

  <h3>O que preciso de você</h3>
  <p>Leia cada mundo como leria o relato de um analista da operadora, e marque: plausível, estranho ou não entendi. A pergunta é se a história poderia ser real e se a resposta faz sentido para você. Depois me diga os mundos que achou estranhos, com uma frase sobre o motivo.</p>

  <h3>Como um mundo é feito</h3>
  <ul class="plain">
    <li>Sorteiam-se de 3 a 8 variáveis da ficha de teoria e um papel para cada uma, entre os que a ficha permite.</li>
    <li>Os sinais dos efeitos vêm da ficha; os tamanhos são sorteados.</li>
    <li>O efeito verdadeiro é calculado simulando os mesmos clientes duas vezes: todos com a oferta e todos sem.</li>
    <li>A história é montada com as frases da ficha, uma por fato, em ordem sorteada. Por isso ela soa mecânica; uma versão em prosa corrida vem depois.</li>
    <li>Cada mundo tem um gêmeo: o mesmo mundo com um único fato trocado, e outra resposta.</li>
  </ul>

  <h3>Como ler os números</h3>
  <p>Cada mundo traz três números na mesma régua: o efeito verdadeiro, a comparação simples entre quem recebeu e quem não recebeu a oferta, e a estimativa com um ajuste. O traço em volta de cada ponto é o intervalo de 95% de confiança. Os valores estão em pontos percentuais de cancelamento.</p>
  <p>{misses}</p>
  {legend}

  <h3>O que já foi medido</h3>
  <p>{_gate_numbers()}</p>

  <h3>Quais mundos estão aqui</h3>
  <p>{html.escape(payload["colophon"])}</p>
</section>
"""
    sheets = [_world_sheet(page, world) for world in worlds]
    body = f'<div class="page doc" lang="pt-BR">{intro}{"".join(sheets)}</div>'
    return _document("Caderno de mundos do Causalista", body)


ROLE_NAME = {
    Role.CONFOUNDER: "Causa da intervenção e do resultado (confundidor)",
    Role.MEDIATOR: "Consequência da intervenção e causa do resultado (mediador)",
    Role.COLLIDER: "Consequência da intervenção e do resultado (colisor)",
    Role.OUTCOME_CAUSE: "Causa só do resultado",
    Role.TREATMENT_CAUSE: "Causa só da intervenção",
    Role.UNRELATED: "Sem relação com a intervenção nem com o resultado",
}
LINK_NAME = {
    "to_treatment": "sobre a intervenção",
    "to_outcome": "sobre o resultado",
    "from_treatment": "da intervenção sobre ela",
    "from_outcome": "do resultado sobre ela",
}
KIND_NAME = {"binary": "sim ou não", "count": "contagem", "continuous": "valor", "score": "nota de 0 a 10"}
STRENGTH_NAME = {
    "to_treatment": "de uma causa sobre a intervenção",
    "to_outcome": "de uma causa sobre o resultado",
    "treatment_to_mediator": "da intervenção sobre um mediador",
    "mediator_to_outcome": "de um mediador sobre o resultado",
    "into_collider": "da intervenção ou do resultado sobre um colisor",
    "direct_effect": "da intervenção diretamente sobre o resultado",
}


def _theory_card(theory: Theory, today: str) -> str:
    def cell(text: str) -> str:
        return text.replace("|", "\\|")

    def number(value: float) -> str:
        return f"{value:g}".replace(".", ",")

    if theory.approved:
        request = [
            "## Situação da ficha",
            "",
            (
                "Esta ficha foi aprovada pelo André e fica aqui para consulta. Ela decide o que os "
                "mundos deste tema podem conter; uma mudança de conteúdo pede nova aprovação dele."
            ),
            "",
        ]
    else:
        request = [
            "## O que preciso de você",
            "",
            (
                "Esta ficha é um rascunho meu. Ela decide o que os mundos deste tema podem conter, "
                "então o conteúdo é decisão sua. Confira:"
            ),
            "",
            "1. se a teoria está enunciada como você a enunciaria, e se as referências estão certas;",
            "2. se cada frase é verdadeira para uma organização real do tema, e se o sinal (+ ou −) está certo;",
            "3. se falta alguma variável importante, ou se alguma deveria sair;",
            "4. se os papéis permitidos para cada variável fazem sentido.",
            "",
            (
                "Pode responder na conversa, apontando a variável e o que mudar. Quando estiver de "
                'acordo, eu troco a situação para "aprovada".'
            ),
            "",
        ]

    lines = [
        f"# Ficha de teoria: {theory.id}",
        "",
        f"{theory.title}. Situação: **{theory.status}**. Exportada em {today}.",
        "",
        *request,
        "## A teoria",
        "",
        f"**{theory.name}.** {theory.statement}",
        "",
        "Referências (a confirmar):",
        "",
        *[f"- {reference}" for reference in theory.references],
        "",
        "## Frases fixas de toda narrativa",
        "",
        "| Uso | Frase |",
        "|---|---|",
        f"| Abertura | {cell(theory.context)} |",
        f"| Quando nada influencia quem recebe a intervenção | {cell(theory.randomized)} |",
        f"| Fecho, nos demais casos | {cell(theory.closing)} |",
        "",
        "## Intervenção e resultado",
        "",
        "| | Coluna | Descrição na tabela | Faixa |",
        "|---|---|---|---|",
        (
            f"| Intervenção | `{theory.treatment.column}` | {cell(theory.treatment.dictionary)} | de "
            f"{number(100 * theory.treatment.range[0])}% a "
            f"{number(100 * theory.treatment.range[1])}% dos clientes |"
        ),
        (
            f"| Resultado | `{theory.outcome.column}` | {cell(theory.outcome.dictionary)} | de "
            f"{number(100 * theory.outcome.range[0])}% a "
            f"{number(100 * theory.outcome.range[1])}% dos clientes |"
        ),
        "",
        (
            "A teoria diz que a intervenção age sobre o resultado com sinal "
            f"**{'+' if theory.effect_sign > 0 else '−'}**."
        ),
        "",
        "## Variáveis",
        "",
        "Em cada frase, o sinal diz o sentido do efeito: **+** aumenta, **−** reduz.",
    ]
    for variable in theory.variables.values():
        typical = number(variable.scale[SCALE_KEY[variable.kind]])
        if variable.kind.value == "binary":
            typical = number(100 * variable.scale["rate"]) + "% dos clientes"
        lines += [
            "",
            f"### `{variable.name}`: {variable.label}",
            "",
            f"Tipo: {KIND_NAME[variable.kind.value]}. Valor típico: {typical}. "
            + (
                f'Pode ficar fora da tabela, com o aviso: "{variable.hidden_fact}"'
                if variable.hidden_fact
                else "Está sempre na tabela."
            ),
            "",
            "| Papel | Descrição na tabela | O que a narrativa diz |",
            "|---|---|---|",
        ]
        for role, spec in variable.roles.items():
            told = [
                f"({'+' if spec.links[name].sign > 0 else '−'}) {LINK_NAME[name]}: {spec.links[name].fact}"
                for name in LINKS_OF_ROLE[role]
            ]
            if spec.fact:
                told.append(spec.fact)
            lines.append(f"| {ROLE_NAME[role]} | {cell(spec.dictionary)} | {cell('<br>'.join(told))} |")

    lines += [
        "",
        "## Decisões de desenho dos mundos",
        "",
        "Estes números valem para todos os temas. São propostas minhas e a decisão é sua.",
        "",
        "| O quê | Valor proposto |",
        "|---|---|",
        "| Variáveis por mundo | de 3 a 8 |",
        "| Mediadores e colisores por mundo | no máximo 2 de cada |",
        "| Mundos não identificáveis | cerca de 40% (gêmeos têm respostas diferentes, então não dá para ser metade) |",
        "| Pares de gêmeos em que o veredito muda | cerca de 3 em 4; nos demais muda só o conjunto de ajuste |",
        "| Mundos em que a intervenção não tem efeito próprio | 15% (30% quando há mediador) |",
        f"| Linhas por tabela | {', '.join(f'{rows:,}'.replace(',', '.') for rows in ROWS)} |",
        "| Sobreposição mínima entre os grupos | ninguém com menos de 2% ou mais de 98% de chance de receber a intervenção |",
        "",
        "Tamanho dos efeitos, na escala de log-chance (ou em desvios-padrão, para variável que não é sim ou não):",
        "",
        "| Efeito | Faixa |",
        "|---|---|",
        *[
            f"| {STRENGTH_NAME[name]} | de {number(low)} a {number(high)} |"
            for name, (low, high) in STRENGTH.items()
        ],
    ]
    rendered = MarkdownIt("commonmark", {"html": True}).enable("table").render("\n".join(lines))
    return _document(f"Ficha de teoria do Causalista: {theory.id}", f'<div class="page prose" lang="pt-BR">{rendered}</div>')


def _markdown_document(path: Path, title: str) -> str:
    rendered = MarkdownIt("commonmark").enable("table").render(path.read_text(encoding="utf-8"))
    return _document(title, f'<div class="page prose" lang="pt-BR">{rendered}</div>')


def _specification() -> tuple[str, str]:
    source = (ROOT / "ESPECIFICACAO.md").read_text(encoding="utf-8")
    revision = re.search(r"Revisão (\d+)", source).group(1)
    rendered = MarkdownIt("commonmark").enable("table").render(source)
    body = f'<div class="page prose" lang="pt-BR">{rendered}</div>'
    return _document(f"Especificação do Causalista (revisão {revision})", body), revision


def _written_cases(today: str) -> str:
    """The hand-written cases of phase 0, one after the other, with the answer the verifier confirmed."""
    cases = load_written_cases()
    lines = [
        "# Casos escritos",
        "",
        f"Entrega da fase 0, exportada em {today}. São {len(cases)} casos escritos pelo assistente, a seu pedido. "
        "A resposta de cada caso foi conferida pelo verificador. Eles não contam como casos escritos por pessoa "
        "e não entram em treino.",
        "",
        "**O que preciso de você:** ler cada caso e dizer se a história soa como uma situação real e se a "
        'resposta é a que você daria. Pode responder "ok" ou apontar o caso e o que mudar.',
    ]
    for number, case in enumerate(cases, start=1):
        lines += ["", f"## Caso {number}: {case.title}", "", f"Tema: {case.theme}. Situação: {case.status}.", ""]
        lines += [case.story, "", "| Coluna | O que é |", "|---|---|"]
        lines += [f"| `{name}` | {text} |" for name, text in case.columns.items()]
        if case.not_in_table:
            lines += ["", "Fora da tabela:", ""]
            lines += [f"- `{name}`: {text}" for name, text in case.not_in_table.items()]
        lines += ["", "**Resposta**", ""]
        if case.identifiable:
            chosen = ", ".join(f"`{name}`" for name in sorted(case.adjust_for)) or "nenhuma coluna"
            lines.append(f"- Identificável. Ajustar por: {chosen}.")
            lines += [f"- Não ajustar por `{name}`: {why}" for name, why in case.do_not_adjust_for.items()]
            if case.indifferent:
                names = ", ".join(f"`{name}`" for name in sorted(case.indifferent))
                lines.append(f"- Indiferente (pode entrar ou não): {names}.")
        else:
            missing = ", ".join(f"`{name}`" for name in sorted(case.missing))
            lines.append(f"- Não identificável. Falta na tabela: {missing}.")
        if case.note:
            lines += ["", case.note]
        if case.twin:
            twin = next(number for number, other in enumerate(cases, start=1) if other.id == case.twin)
            lines += ["", f"Este caso é gêmeo do caso {twin}: a mesma história, com um fato trocado."]
    rendered = MarkdownIt("commonmark").enable("table").render("\n".join(lines))
    return _document("Casos escritos do Causalista", f'<div class="page prose" lang="pt-BR">{rendered}</div>')


def _guide(
    revision: str, cases: int, worlds: int, theory: Theory, neighbours: bool, status: bool, today: str,
    drafts: list[Theory],
) -> str:  # fmt: skip
    extra = ""
    if neighbours:
        extra += (
            "| 07 Trabalhos vizinhos.pdf | o que já existe na literatura perto deste projeto | "
            "saber o que podemos e o que não podemos chamar de novo |\n"
        )
    if status:
        extra += (
            "| 08 Status do projeto.pdf | tudo o que foi feito até agora, fase por fase | "
            "o relato completo, com os números de cada etapa |\n"
        )
    cards = "".join(
        f"| {number} Ficha de teoria - {draft.id}.pdf | a ficha do tema {draft.id}: variáveis, papéis, sinais e frases | "
        "revisada e aprovada por delegação; fica para consulta |\n"
        for number, draft in enumerate(drafts, start=11)
    )
    source = f"""
# Causalista: comece aqui

Material de leitura, exportado do repositório em {today}.

## Onde estamos, em poucas palavras

Pense em um aluno, uma prova e um gabarito.

- **O gabarito** (o verificador) está pronto e foi aprovado por você.
- **Os exercícios e a prova** saem de oito fichas de teoria, uma por tema. Você decidiu não ler tudo um a um. Em troca, cada ficha foi lida de novo, frase por frase, por um revisor independente, e corrigida. Nessa revisão também foram fechadas três "colas": maneiras de acertar a prova sem raciocinar.
- **O aluno** (o modelo pequeno) já fez treinos de teste, de cerca de meia hora cada. Sem treino ele acerta metade da prova; depois do treino, quase tudo.
- **O que ainda não está bom.** Quando a história é contada de um jeito diferente do dos exercícios (texto corrido, casos escritos à mão), o aluno treinado erra mais. Ele ainda lê melhor as frases dos exercícios do que um texto qualquer.
- **O passo em andamento.** Pôr histórias em texto corrido no treino e medir de novo.

Os números e o relato completo estão no arquivo 08.

## O que preciso de você

Nada disto impede o trabalho de continuar.

1. **Os dois temas guardados só para a prova.** Em uso: e-mail marketing e saúde suplementar.
2. **Os idiomas.** Proponho treinar em português, inglês e espanhol e guardar francês e alemão para a prova. Os treinos de teste são só em português.
3. **Uma chave de API de um modelo de fronteira**, para comparar no placar.
4. **Organização no Hugging Face**: abrir a conta e alinhar com a escola o uso do nome COPPEAD.

## O que há nesta pasta

| Arquivo | O que é | Para quê |
|---|---|---|
| 01 Caderno de casos.pdf | os {cases} casos de resposta conhecida, um por página, com diagrama | já aprovado; fica para consulta |
| 02 Especificação.pdf | o que estamos construindo e em que ordem (revisão {revision}) | consulta; a seção 13 registra cada etapa |
| 03 Casos interativos.html | os mesmos casos, para explorar clicando nas colunas | mostrar o conceito aos colegas |
| 04 Ficha de teoria - {theory.id}.pdf | o que a teoria diz sobre o tema: variáveis, papéis, sinais e frases | aprovada por você; frases corrigidas na revisão |
| 05 Caderno de mundos.pdf | {worlds} mundos gerados a partir da ficha, com história, diagrama e números | consulta; os mundos mudaram depois das correções |
| 06 Mundos interativos.html | os mesmos mundos, para explorar clicando nas colunas | ver o que cada escolha faz com o número |
{extra}| 09 Casos escritos.pdf | cinco casos com história, colunas e resposta, conferidos pelo verificador | revisados e aprovados por delegação; consulta |
| 10 Fichas para aprovar.pdf | as escolhas de teoria mais discutíveis de cada ficha nova | se quiser olhar só o essencial das fichas |
{cards}
Os arquivos 03 e 06 abrem no navegador do computador, com duplo clique. As mesmas páginas estão na pasta `pages/` do conjunto de dados no Hugging Face.


## Qual versão vale

Estes arquivos são cópias para leitura. A versão que vale é a do repositório, e as cópias são refeitas com `scripts/reading_pack.py`.
"""
    rendered = MarkdownIt("commonmark").enable("table").render(source)
    return _document("Causalista: comece aqui", f'<div class="page prose" lang="pt-BR">{rendered}</div>')


def _print(page: Page, source: Path, target: Path, label: str) -> None:
    page.goto(source.as_uri())
    page.wait_for_load_state("networkidle")
    page.evaluate("() => document.fonts.ready.then(() => true)")
    footer = (
        '<div style="width:100%;font-size:8px;color:#4B5969;padding:0 16mm;display:flex;'
        'justify-content:space-between;font-family:sans-serif;">'
        f"<span>{html.escape(label)}</span>"
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
    )
    page.pdf(
        path=str(target),
        format="A4",
        print_background=True,
        margin=MARGIN,
        display_header_footer=True,
        header_template="<div></div>",
        footer_template=footer,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the reading pack.")
    parser.add_argument("--to", type=Path, help="also copy the files to this folder")
    parser.add_argument("--theory", default="telecom")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    work = OUTPUT / "_montagem"
    work.mkdir(exist_ok=True)
    today = datetime.datetime.now().astimezone().strftime("%d/%m/%Y")

    cases = load_textbook_cases()
    case_data = gallery_payload(cases)
    theory = load_theory(args.theory)
    world_data = worlds_payload(theory)
    neighbours = ROOT / "docs" / "trabalhos-vizinhos.md"
    status = ROOT / "docs" / "status.md"
    points = ROOT / "docs" / "fichas-para-aprovar.md"
    others = sorted(path.stem for path in THEORIES_DIR.glob("*.yaml") if path.stem != args.theory)
    drafts = [load_theory(theory_id) for theory_id in others]
    spec_html, revision = _specification()

    case_page = OUTPUT / "03 Casos interativos.html"
    case_page.write_text(render(cases, standalone=True), encoding="utf-8")
    world_page = OUTPUT / "06 Mundos interativos.html"
    world_page.write_text(render_page(world_data, worlds_text(theory), standalone=True), encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="light")
        page = context.new_page()

        page.goto(case_page.as_uri())
        page.wait_for_load_state("networkidle")
        case_booklet = _booklet(page, case_data, today)
        page.goto(world_page.as_uri())
        page.wait_for_load_state("networkidle")
        world_booklet = _world_booklet(page, world_data, today)

        guide = _guide(
            revision,
            len(cases),
            len(world_data["cases"]),
            theory,
            neighbours.exists(),
            status.exists(),
            today,
            drafts,
        )
        documents = [
            ("00 Comece aqui.pdf", guide, "Causalista · Comece aqui"),
            ("01 Caderno de casos.pdf", case_booklet, "Causalista · Caderno de casos"),
            ("02 Especificação.pdf", spec_html, f"Causalista · Especificação (revisão {revision})"),
            (
                f"04 Ficha de teoria - {theory.id}.pdf",
                _theory_card(theory, today),
                f"Causalista · Ficha de teoria: {theory.id} ({theory.status})",
            ),
            ("05 Caderno de mundos.pdf", world_booklet, "Causalista · Caderno de mundos"),
        ]
        if neighbours.exists():
            documents.append(
                (
                    "07 Trabalhos vizinhos.pdf",
                    _markdown_document(neighbours, "Trabalhos vizinhos do Causalista"),
                    "Causalista · Trabalhos vizinhos",
                )
            )
        if status.exists():
            documents.append(
                (
                    "08 Status do projeto.pdf",
                    _markdown_document(status, "Status do projeto Causalista"),
                    "Causalista · Status do projeto",
                )
            )
        documents.append(("09 Casos escritos.pdf", _written_cases(today), "Causalista · Casos escritos"))
        if points.exists():
            documents.append(
                (
                    "10 Fichas para aprovar.pdf",
                    _markdown_document(points, "Fichas de teoria para aprovar"),
                    "Causalista · Fichas para aprovar",
                )
            )
        for number, draft in enumerate(drafts, start=11):
            documents.append(
                (
                    f"{number} Ficha de teoria - {draft.id}.pdf",
                    _theory_card(draft, today),
                    f"Causalista · Ficha de teoria: {draft.id} ({draft.status})",
                )
            )
        files = [case_page, world_page]
        for number, (name, markup, label) in enumerate(documents):
            source = work / f"{number}.html"
            source.write_text(markup, encoding="utf-8")
            _print(page, source, OUTPUT / name, label)
            files.append(OUTPUT / name)
        browser.close()

    files.sort(key=lambda file: file.name)
    for file in files:
        print(f"wrote {file.relative_to(ROOT)} ({file.stat().st_size / 1024:.0f} KB)")
    if args.to:
        args.to.mkdir(parents=True, exist_ok=True)
        for file in files:
            shutil.copyfile(file, args.to / file.name)
        print(f"copied {len(files)} files to {args.to}")


if __name__ == "__main__":
    main()
