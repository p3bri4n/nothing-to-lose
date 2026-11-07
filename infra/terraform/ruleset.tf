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

    # Une approbation est requise (décision 0021). Les agents travaillent avec un compte machine
    # (rôle Write, voir collaborator.tf) : il n'a pas de contournement et ne peut pas approuver sa
    # propre pull request, donc il ne peut pas fusionner seul. Le propriétaire approuve, ou fusionne
    # en contournant (bypass_actors ci-dessus) ; ses propres pull requests passent par le contournement.
    # Attention : une fois la PR approuvée, la fusion est ouverte à tout compte Write, le compte
    # machine compris. Le propriétaire approuve donc au moment de fusionner (ou fusionne par contournement).
    pull_request {
      required_approving_review_count   = 1
      dismiss_stale_reviews_on_push     = true
      required_review_thread_resolution = true
      # Le dernier push doit être approuvé par quelqu'un d'autre que son auteur : le compte machine
      # ne peut pas pousser sur la branche d'une PR puis l'approuver lui-même.
      require_last_push_approval = true
      # L'approbation doit venir d'un propriétaire du code (.github/CODEOWNERS : le propriétaire du
      # dépôt). Sans cela, tout compte Write pourrait approuver : les approbations du compte machine
      # (ou d'un second compte) ne comptent pas. Le fichier CODEOWNERS doit exister et rester valide.
      require_code_owner_review = true
    }

    required_status_checks {
      strict_required_status_checks_policy = true

      required_check {
        context = var.required_ci_check
      }
    }
  }
}
