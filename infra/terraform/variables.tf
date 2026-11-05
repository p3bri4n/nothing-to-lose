variable "github_owner" {
  description = "Compte GitHub propriétaire du dépôt."
  type        = string
}

variable "repository_name" {
  description = "Nom du dépôt."
  type        = string
  default     = "say-again"
}

variable "repository_description" {
  description = "Description affichée sur GitHub."
  type        = string
  default     = "Say Again : Toulouse — invasion zombie simulée par IA. Zombies pilotés par Laya, survivants par un LLM local, ordres transmis par une radio qui grésille."
}

variable "required_ci_check" {
  description = "Nom du job de CI obligatoire avant fusion sur la branche principale."
  type        = string
  default     = "ci-cpu"
}

variable "gpu_eval_enabled" {
  description = "Active le workflow d'évaluation sur le runner GPU auto-hébergé (à passer à true au jalon P2)."
  type        = bool
  default     = false
}

variable "deploy_enabled" {
  description = "Active le déploiement du viewer sur Cloudflare Pages (à passer à true au jalon du replay public)."
  type        = bool
  default     = false
}

variable "cloudflare_account_id" {
  description = "Identifiant du compte Cloudflare (laisser vide tant que le déploiement n'est pas configuré)."
  type        = string
  default     = ""
}

variable "cloudflare_api_token" {
  description = "Jeton d'API Cloudflare limité à Pages (laisser vide tant que le déploiement n'est pas configuré)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "cloudflare_pages_project" {
  description = "Nom du projet Cloudflare Pages."
  type        = string
  default     = "say-again"
}
