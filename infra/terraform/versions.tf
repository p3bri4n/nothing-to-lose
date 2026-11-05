terraform {
  required_version = ">= 1.6"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }

  # État local, hors du dépôt (décision 0002).
  # Le chemin est fourni à l'initialisation : voir `just tf-init`.
  backend "local" {}
}
