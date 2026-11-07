# Protection de la branche principale : passage par une pull request,
# CI obligatoire, historique linéaire, ni suppression ni force-push.
resource "github_repository_ruleset" "default_branch" {
  name        = "branche-principale"
  repository  = github_repository.main.name
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  # Le propriétaire (rôle « admin » du dépôt) ne pousse jamais directement sur la branche principale :
  # il passe par une pull request, qu'il peut fusionner en contournant la CI en cas d'urgence.
  # actor_id 5 = rôle de dépôt « admin » : à vérifier si GitHub change ces identifiants.
  bypass_actors {
    actor_id    = 5
    actor_type  = "RepositoryRole"
    bypass_mode = "pull_request"
  }

  rules {
    deletion                = true
    non_fast_forward        = true
    required_linear_history = true

    pull_request {
      required_approving_review_count   = 0
      dismiss_stale_reviews_on_push     = true
      required_review_thread_resolution = true
    }

    required_status_checks {
      strict_required_status_checks_policy = true

      required_check {
        context = var.required_ci_check
      }
    }
  }
}
