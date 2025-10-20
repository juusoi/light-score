variable "service_name" {
  description = "Lightsail Container Service name"
  type        = string
  default     = "lightscore-prod"
}

variable "power" {
  description = "Instance size for Lightsail Container Service"
  type        = string
  default     = "nano" # nano | micro | small | medium | large | xlarge | 2xlarge
}

variable "scale" {
  description = "Number of nodes"
  type        = number
  default     = 1
}

variable "subdomain" {
  description = "Subdomain to point at the service"
  type        = string
  default     = "stg.lightscore.fi"
}
