locals {
  labels = {
    "décision"     = { color = "8250df", description = "Décision structurante à poser à l'utilisateur" }
    "bug"          = { color = "d73a4a", description = "Comportement incorrect" }
    "régression"   = { color = "b60205", description = "Quelque chose qui marchait ne marche plus" }
    "déterminisme" = { color = "fbca04", description = "Replay ou simulation non reproductible" }
    "retour"       = { color = "0e8a16", description = "Retour de visionnage (feedback/)" }
    "jalon:PP"     = { color = "c5def5", description = "Préparation de l'environnement" }
    "jalon:P0"     = { color = "c5def5", description = "Carte minimale" }
    "jalon:P1"     = { color = "c5def5", description = "Simulation de base" }
    "jalon:P2"     = { color = "c5def5", description = "Pont IA" }
    "jalon:P3"     = { color = "c5def5", description = "Zombies Laya" }
    "jalon:P4"     = { color = "c5def5", description = "Survivants LLM" }
    "jalon:P5"     = { color = "c5def5", description = "Test du concept" }
  }
}

resource "github_issue_label" "project" {
  for_each    = local.labels
  repository  = github_repository.main.name
  name        = each.key
  color       = each.value.color
  description = each.value.description
}
