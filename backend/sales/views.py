# backend/sales/views.py
from collections import defaultdict
import datetime
from decimal import Decimal
import logging
import os

from django.db import transaction 
from django.db.models import Sum, Avg
from django.utils import timezone
import pandas as pd
from pandas.errors import EmptyDataError
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business
from utils.square_api import fetch_and_save_square_sales_data

from .models import SalesData, SalesDataPoint

logger = logging.getLogger(__name__)

class SalesDataView(APIView):
    """
    API view for uploading and listing sales data files.
    GET: List all sales data files for the authenticated user's business.
    POST: Upload a sales data file (CSV only).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """
        Get sales data chart for the authenticated user's business.
        
        This endpoint returns:
        1. Overall daily revenue chart
        2. Top 5 best-selling products
        3. Bottom 5 worst-selling products
        """
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        # Get date filter from query parameters
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        
        if start_date_param:
            try:
                start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date_param:
            try:
                end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 1. Get overall daily sales data
        data_points = SalesDataPoint.objects.filter(
            business=business,
            date__gte=start_date,
            date__lte=end_date
        ).values('date').annotate(
            total_revenue=Sum('revenue')
        ).order_by('date')
        
        if not data_points.exists():
            return Response({
                "overall_sales": {
                    "square_connected": bool(business.square_access_token),
                    "labels": [],
                    "datasets": []
                },
                "top_products": {
                    "chart": {"labels": [], "datasets": []},
                    "summary": []
                },
                "bottom_products": {
                    "chart": {"labels": [], "datasets": []},
                    "summary": []
                }
            })
        
        # Format the date labels for chart.js (common for all charts)
        labels = [entry['date'].strftime('%d-%m-%Y') for entry in data_points]
        
        # Format the overall revenue data
        values = [float(entry['total_revenue']) for entry in data_points]
        
        overall_chart_data = {
            "square_connected": bool(business.square_access_token),
            "labels": labels,
            "datasets": [{
                "label": "Daily Sales",
                "data": values,
                "fill": False,
                "borderColor": "rgb(75, 192, 192)",
                "tension": 0.1
            }]
        }
        
        # 2. Get product performance data - aggregated over whole period
        product_data = SalesDataPoint.objects.filter(
            business=business,
            date__gte=start_date,
            date__lte=end_date,
            product_name__isnull=False  # Only include data points with product name
        ).values('product_name').annotate(
            total_revenue=Sum('revenue'),
            total_units=Sum('units_sold'),
            average_price=Avg('product_price')
        ).order_by('-total_units')
        
        # Get top 3 and bottom 3 products
        top_products = list(product_data[:3])
        bottom_products = list(product_data.order_by('total_units')[:3])
        
        # 3. Get all product sales by date for selected products
        top_product_names = [p['product_name'] for p in top_products if p['product_name']]
        bottom_product_names = [p['product_name'] for p in bottom_products if p['product_name']]
        
        # Get daily data for all products in the selected groups
        daily_product_data = SalesDataPoint.objects.filter(
            business=business,
            date__gte=start_date,
            date__lte=end_date,
            product_name__in=top_product_names + bottom_product_names
        ).values('date', 'product_name').annotate(
            daily_revenue=Sum('revenue')
        ).order_by('date')
        
        # Organize data by product and date
        top_products_by_date = defaultdict(lambda: defaultdict(float))
        bottom_products_by_date = defaultdict(lambda: defaultdict(float))
        
        # Fill data for each day and product
        for entry in daily_product_data:
            date_str = entry['date'].strftime('%d-%m-%Y')
            product_name = entry['product_name']
            revenue = float(entry['daily_revenue'])
            
            # Store in correct category (top or bottom)
            if product_name in top_product_names:
                top_products_by_date[date_str][product_name] = revenue
            
            if product_name in bottom_product_names:
                bottom_products_by_date[date_str][product_name] = revenue
        
        # Create datasets for chart.js
        top_datasets = []
        bottom_datasets = []
        
        # Colors for the charts
        colors = ['#FF6384', '#36A2EB', '#FFCE56']
        
        # Create datasets for top products
        for i, product_name in enumerate(top_product_names):
            if not product_name:
                continue

            data = []
            
            for date_str in labels:
                data.append(top_products_by_date[date_str][product_name])
            
            top_datasets.append({
                "label": product_name,
                "data": data,
                "fill": False,
                "borderColor": colors[i % len(colors)],
                "tension": 0.1
            })
        
        # Create datasets for bottom products
        for i, product_name in enumerate(bottom_product_names):
            if not product_name:
                continue
                
            data = []
            
            for date_str in labels:
                data.append(bottom_products_by_date[date_str][product_name])
            
            bottom_datasets.append({
                "label": product_name,
                "data": data,
                "fill": False,
                "borderColor": colors[i % len(colors)],
                "tension": 0.1
            })
        
        # Create final chart data format
        top_chart = {
            "labels": labels,
            "datasets": top_datasets
        }
        
        bottom_chart = {
            "labels": labels,
            "datasets": bottom_datasets
        }
        
        # Prepare the final response
        return Response({
            "overall_sales": overall_chart_data,
            "top_products": {
                "chart": top_chart,
                "summary": top_products
            },
            "bottom_products": {
                "chart": bottom_chart,
                "summary": bottom_products
            }
        })
    
    def post(self, request):
        """Handle sales data file upload"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_obj = request.FILES['file']
        filename = file_obj.name
        file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
        
        # Validate file type
        if file_extension != 'csv':
            return Response({"error": f"Unsupported file format: {file_extension}. Please upload CSV."}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Create sales data record
        sales_data = SalesData.objects.create(
            business=business,
            file=file_obj,
            filename=filename,
            file_type=file_extension,
            processed=True,
            processed_at=timezone.now()
        )
        
        try:
            file_obj.seek(0)
            df = pd.read_csv(file_obj)

            if df.empty:
                logger.warning("⚠️ CSV upload failed — File has headers but no data rows.")
                return Response({"error": "The uploaded file contains no data rows."}, status=status.HTTP_400_BAD_REQUEST)

            # Check required columns - adjusted for product-level data
            required_columns = ['Date', 'Product Name', 'Price', 'Quantity']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response({
                    "error": f"CSV must have these columns: {', '.join(required_columns)}. Missing: {', '.join(missing_columns)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process the CSV data
            try:
                df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d', errors='raise')
            except ValueError:
                try:
                    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='raise')
                except ValueError:
                    try:
                        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='raise')
                    except ValueError:
                        sample_date = df['Date'].iloc[0] if not df.empty else "N/A"
                        return Response({
                            "error": f"Date format not recognized. Please use YYYY-MM-DD format. Sample date in your file: '{sample_date}'"
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
            df['DateOnly'] = df['Date'].dt.date
            
            # Calculate revenue for each row
            df['Revenue'] = df['Price'].astype(float) * df['Quantity'].astype(int)
            
            grouped_df = df.groupby(['DateOnly', 'Product Name', 'Price']).agg({
                'Quantity': 'sum',
                'Revenue': 'sum'
            }).reset_index()

            dates = grouped_df['DateOnly'].unique().tolist()
            product_names = grouped_df['Product Name'].unique().tolist()

            existing_records = {}
            for record in SalesDataPoint.objects.filter(
                business=business,
                date__in=dates,
                product_name__in=product_names,
                source='upload'
            ):
                key = (record.date, record.product_name, record.product_price)
                existing_records[key] = record

            records_to_update = []
            records_to_create = []

            for _, row in grouped_df.iterrows():
                date = row['DateOnly']
                product_name = row['Product Name']
                price = float(row['Price'])
                quantity = int(row['Quantity'])
                revenue = float(row['Revenue'])
                
                key = (date, product_name, price)
                
                if key in existing_records:
                    record = existing_records[key]
                    record.units_sold += quantity
                    record.revenue += Decimal(str(revenue))
                    records_to_update.append(record)
                else:
                    record = SalesDataPoint(
                        business=business,
                        date=date,
                        product_name=product_name,
                        product_price=price,
                        units_sold=quantity,
                        revenue=revenue,
                        source_file=sales_data,
                        source='upload'
                    )
                    records_to_create.append(record)

            with transaction.atomic():
                if records_to_update:
                    SalesDataPoint.objects.bulk_update(
                        records_to_update, 
                        ['units_sold', 'revenue']
                    )
                
                if records_to_create:
                    SalesDataPoint.objects.bulk_create(records_to_create)
            
            return Response({
                "success": True,
                "message": f"Successfully uploaded."
            }, status=status.HTTP_201_CREATED)
        
        except EmptyDataError:
            logger.error("❌ CSV upload failed — No readable content or missing columns (EmptyDataError)", exc_info=True)
            return Response({"error": "The uploaded file is empty or does not contain valid columns."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"❌ CSV upload failed — {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RefreshSalesDataView(APIView):
    """
    API view for refreshing sales data from Square.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Refresh sales data from Square API"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            fetch_and_save_square_sales_data(business)
            return Response({"success": True}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("❌ Refresh sales data failed — %s", str(e), exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)