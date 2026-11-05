# Environnement de déploiement : seuls les workflows de la branche
# principale peuvent l'utiliser, et ses secrets n'existent que là.
resource "github_repository_environment" "production" {
  repository  = github_repository.main.name
  environment = "production"

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "production_main" {
  repository     = github_repository.main.name
  environment    = github_repository_environment.production.environment
  branch_pattern = "main"
}

# Secrets Cloudflare, créés seulement une fois le jeton fourni (décision 0004).
resource "github_actions_environment_secret" "cloudflare_api_token" {
  count           = var.cloudflare_api_token != "" ? 1 : 0
  repository      = github_repository.main.name
  environment     = github_repository_environment.production.environment
  secret_name     = "CLOUDFLARE_API_TOKEN"
  plaintext_value = var.cloudflare_api_token
}

resource "github_actions_environment_secret" "cloudflare_account_id" {
  count           = var.cloudflare_account_id != "" ? 1 : 0
  repository      = github_repository.main.name
  environment     = github_repository_environment.production.environment
  secret_name     = "CLOUDFLARE_ACCOUNT_ID"
  plaintext_value = var.cloudflare_account_id
}
