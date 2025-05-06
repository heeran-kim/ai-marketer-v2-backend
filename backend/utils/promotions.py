from sales.models import SalesDataPoint
from django.db.models import Sum
from promotions.models import Promotion
from django.db.models import Q

def update_promotion_sold_counts(business, product_names, date_range):
    """Update sold counts for active promotions based on newly uploaded sales data"""
    if not product_names:
        return

    # Find active promotions that involve these products
    active_promotions = Promotion.objects.filter(
        Q(business=business) &
        (Q(end_date__isnull=True) | Q(end_date__gte=date_range[0])) &
        Q(start_date__lte=date_range[1])
    )
    
    for promotion in active_promotions:
        # Determine product names for this promotion
        promotion_product_names = (
            [product['name'] for product in promotion.product_data]
            if promotion.product_data
            else promotion.product_names
        )

        # Check if any promotion products match uploaded product names
        if any(product in product_names for product in promotion_product_names):
            # Calculate total units sold for these products within promotion date range
            promotion_start = max(promotion.start_date, date_range[0])
            promotion_end = min(promotion.end_date or date_range[1], date_range[1])
            
            product_sales = SalesDataPoint.objects.filter(
                business=business,
                product_name__in=promotion_product_names,
                date__range=(promotion_start, promotion_end)
            ).aggregate(total_units=Sum('units_sold'))['total_units'] or 0
            
            # Update the promotion with the new count
            promotion.sold_count = product_sales
            promotion.save(update_fields=['sold_count'])