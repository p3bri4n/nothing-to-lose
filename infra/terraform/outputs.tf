output "repository_url" {
  description = "Adresse du dépôt."
  value       = github_repository.main.html_url
}

output "repository_ssh_url" {
  description = "Adresse SSH à utiliser comme remote Git."
  value       = github_repository.main.ssh_clone_url
}

output "agents_account" {
  description = "Compte machine des agents invité sur le dépôt (vide si aucun)."
  value       = var.agents_account
}
