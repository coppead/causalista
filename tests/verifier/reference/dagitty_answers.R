# Ask dagitty about each problem in a JSON file and write its answers to another.
# Called by make_dagitty_reference.py; not meant to be run by hand.

suppressMessages(library(dagitty))
suppressMessages(library(jsonlite))

args <- commandArgs(trailingOnly = TRUE)
problems <- fromJSON(args[1], simplifyVector = FALSE)

build <- function(p, with_latents) {
  latent <- unlist(p$latent)
  node_lines <- sapply(p$nodes, function(n) {
    tags <- c()
    if (n == p$treatment) tags <- c(tags, "exposure")
    if (n == p$outcome) tags <- c(tags, "outcome")
    if (with_latents && n %in% latent) tags <- c(tags, "latent")
    if (length(tags)) paste0(n, " [", paste(tags, collapse = ","), "]") else n
  })
  edge_lines <- sapply(p$edges, function(e) paste(e[[1]], "->", e[[2]]))
  dagitty(paste("dag {", paste(c(node_lines, edge_lines), collapse = " ; "), "}"))
}

answers <- lapply(problems, function(p) {
  plain <- build(p, FALSE)
  with_latents <- build(p, TRUE)
  valid <- sapply(p$sets, function(z) {
    isAdjustmentSet(plain, unlist(z), exposure = p$treatment, outcome = p$outcome)
  })
  all_sets <- adjustmentSets(with_latents, type = "all")
  canonical <- adjustmentSets(with_latents, type = "canonical")
  list(
    id = p$id,
    valid = as.list(as.logical(valid)),
    all_sets = lapply(all_sets, function(s) as.list(sort(as.character(s)))),
    identifiable = length(canonical) > 0
  )
})

meta <- list(
  dagitty = as.character(packageVersion("dagitty")),
  r = R.version.string
)
write_json(list(meta = meta, answers = answers), args[2], auto_unbox = TRUE)
