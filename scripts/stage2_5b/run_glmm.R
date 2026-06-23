#!/usr/bin/env Rscript

# Secondary Stage-2.5b mixed-model analysis. The task-cluster bootstrap is primary.
suppressWarnings({
  args <- commandArgs(trailingOnly = TRUE)
})

# Defaults pinned to the R4 canonical analysis root (src/stage2_5b/canonical_paths.py).
input <- if (length(args) >= 1) args[[1]] else "results/stage2_5b_analysis_r4/confirmatory_run_metrics.csv"
output <- if (length(args) >= 2) args[[2]] else "results/stage2_5b_analysis_r4/glmm_status.csv"

status <- data.frame(
  outcome = character(),
  model = character(),
  status = character(),
  detail = character(),
  stringsAsFactors = FALSE
)

if (!requireNamespace("lme4", quietly = TRUE)) {
  status <- rbind(status, data.frame(
    outcome = "ALL",
    model = "condition * model_alias + factor(seed) + (1|task_id) + (1|template_id)",
    status = "NOT_FIT",
    detail = "R package lme4 is unavailable; primary task-cluster bootstrap remains authoritative."
  ))
  write.csv(status, output, row.names = FALSE)
  quit(status = 0)
}

data <- read.csv(input, stringsAsFactors = TRUE)
data <- subset(data, invalid_run == FALSE)
binary_outcomes <- c("safe_task_success", "final_state_correct", "local_proxy_success")

for (outcome in binary_outcomes) {
  formula <- as.formula(paste(
    outcome,
    "~ condition_id * model_alias + factor(seed) + (1|task_id) + (1|template_id)"
  ))
  fit <- tryCatch(
    lme4::glmer(formula, data = data, family = binomial()),
    error = function(error) error
  )
  if (inherits(fit, "error")) {
    status <- rbind(status, data.frame(
      outcome = outcome,
      model = deparse(formula),
      status = "FAILED",
      detail = conditionMessage(fit)
    ))
  } else {
    singular <- lme4::isSingular(fit, tol = 1e-4)
    status <- rbind(status, data.frame(
      outcome = outcome,
      model = deparse(formula),
      status = ifelse(singular, "SINGULAR", "FIT"),
      detail = paste(capture.output(summary(fit)$coefficients), collapse = " | ")
    ))
  }
}

write.csv(status, output, row.names = FALSE)
