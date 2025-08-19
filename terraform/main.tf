resource "aws_lightsail_container_service" "svc" {
  name  = var.service_name
  power = var.power
  scale = var.scale
}

# Convenience: strip "https://" so you can CNAME to this hostname
locals {
  svc_hostname = replace(aws_lightsail_container_service.svc.url, "https://", "")
}

################
#    Outputs   #
################

output "lightsail_service_name" {
  value       = aws_lightsail_container_service.svc.name
  description = "Lightsail Container Service name"
}

output "lightsail_service_url" {
  value       = aws_lightsail_container_service.svc.url
  description = "Public HTTPS URL of the service"
}

output "dns_target_hostname" {
  value       = local.svc_hostname
  description = "Point your CNAME to this hostname"
}