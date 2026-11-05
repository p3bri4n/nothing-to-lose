# Le jeton GitHub est lu dans la variable d'environnement GITHUB_TOKEN.
# Il ne doit jamais apparaître dans un fichier du dépôt.
provider "github" {
  owner = var.github_owner
}
