# Compte machine des agents (décision 0021, étape E10b).
# Rôle Write (permission "push") : peut pousser des branches et ouvrir des pull requests, mais ne
# contourne pas le ruleset et ne peut pas approuver sa propre pull request. Jamais "admin" ni "maintain".
# Créé seulement si agents_account est renseigné. Sur un dépôt personnel, le provider n'accepte que "push".
# GitHub envoie une invitation : le compte machine doit l'accepter (docs/technique/compte-machine-agents.md).
resource "github_repository_collaborator" "agents" {
  count = var.agents_account == "" ? 0 : 1

  repository = github_repository.main.name
  username   = var.agents_account
  permission = "push"

  lifecycle {
    precondition {
      condition     = lower(var.agents_account) != lower(var.github_owner)
      error_message = "agents_account ne doit pas être le propriétaire du dépôt : les agents utilisent un compte distinct."
    }
  }
}
