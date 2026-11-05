# Dépôt public dès le départ (décision 0003).
resource "github_repository" "main" {
  name        = var.repository_name
  description = var.repository_description
  visibility  = "public"
  topics      = ["ai", "agents", "llm", "rust", "webassembly", "threejs", "simulation", "toulouse"]

  has_issues      = true
  has_projects    = false
  has_wiki        = false
  has_discussions = false

  # Pas d'initialisation : l'historique local est poussé tel quel.
  auto_init = false

  allow_squash_merge     = true
  allow_merge_commit     = false
  allow_rebase_merge     = false
  delete_branch_on_merge = true

  # Les alertes de vulnérabilités sont gérées par github_repository_vulnerability_alerts (ci-dessous).

  security_and_analysis {
    secret_scanning {
      status = "enabled"
    }
    secret_scanning_push_protection {
      status = "enabled"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "github_repository_vulnerability_alerts" "main" {
  repository = github_repository.main.name
  enabled    = true
}
