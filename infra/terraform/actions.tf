# Dépôt public : seules les actions de GitHub, des éditeurs vérifiés
# et une courte liste explicite sont autorisées.
resource "github_actions_repository_permissions" "main" {
  repository      = github_repository.main.name
  enabled         = true
  allowed_actions = "selected"

  allowed_actions_config {
    github_owned_allowed = true
    verified_allowed     = true
    patterns_allowed = [
      "dtolnay/rust-toolchain@*",
      "Swatinem/rust-cache@*",
      "extractions/setup-just@*",
      "astral-sh/setup-uv@*",
      "cloudflare/wrangler-action@*",
    ]
  }
}

# Interrupteurs lus par les workflows (vars.*).
resource "github_actions_variable" "gpu_eval_enabled" {
  repository    = github_repository.main.name
  variable_name = "GPU_EVAL_ENABLED"
  value         = tostring(var.gpu_eval_enabled)
}

resource "github_actions_variable" "deploy_enabled" {
  repository    = github_repository.main.name
  variable_name = "DEPLOY_ENABLED"
  value         = tostring(var.deploy_enabled)
}

resource "github_actions_variable" "cloudflare_pages_project" {
  repository    = github_repository.main.name
  variable_name = "CLOUDFLARE_PAGES_PROJECT"
  value         = var.cloudflare_pages_project
}
