#!/bin/bash
# Script to delete inactive customers (no orders in the last year)
# Logs results to /tmp/customer_cleanup_log.txt

timestamp=$(date "+%Y-%m-%d %H:%M:%S")

deleted_count=$(python3 manage.py shell -c "
from crm.models import Customer
from django.utils import timezone
from datetime import timedelta

one_year_ago = timezone.now() - timedelta(days=365)
inactive_customers = Customer.objects.filter(orders__isnull=True) | Customer.objects.exclude(orders__created_at__gte=one_year_ago)
deleted, _ = inactive_customers.delete()
print(deleted)
")

echo \"[$timestamp] Deleted $deleted_count inactive customers.\" >> /tmp/customer_cleanup_log.txt
