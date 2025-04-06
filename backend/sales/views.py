# backend/sales/views.py
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from businesses.models import Business
from .models import SalesData, SalesDataPoint
from .serializers import SalesDataSerializer

import os
import pandas as pd
from pandas.errors import EmptyDataError

import logging
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
        """List daily sales data for the authenticated user's business"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        data_points = SalesDataPoint.objects.filter(business=business).order_by('date')
        
        if not data_points.exists():
            return Response({"labels": [], "datasets": []})

        labels = [entry.date.strftime('%d-%m-%Y') for entry in data_points]
        values = [float(entry.revenue) for entry in data_points]
        
        return Response({
            "labels": labels,
            "datasets": [{
                "label": "Sales",
                "data": values,
            }]
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
            file_type=file_extension
        )
        
        try:
            file_obj.seek(0)
            df = pd.read_csv(file_obj)

            if df.empty:
                logger.warning("⚠️ CSV upload failed — File has headers but no data rows.")
                return Response({"error": "The uploaded file contains no data rows."}, status=status.HTTP_400_BAD_REQUEST)

            if 'Date' not in df.columns or 'Total Amount' not in df.columns:
                return Response({"error": "CSV must have 'Date' and 'Total Amount' columns"}, status=status.HTTP_400_BAD_REQUEST)
            
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
            df['DateOnly'] = df['Date'].dt.date
            
            grouped = df.groupby('DateOnly')['Total Amount'].sum().reset_index()
            
            for _, row in grouped.iterrows():
                date = row['DateOnly']
                revenue = float(row['Total Amount'])

                SalesDataPoint.objects.update_or_create(
                    business=business,
                    date=date,
                    defaults={
                        'revenue': revenue,
                        'source_file': sales_data
                    }
                )
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        
        except EmptyDataError:
            logger.error("❌ CSV upload failed — No readable content or missing columns (EmptyDataError)", exc_info=True)
            return Response({"error": "The uploaded file is empty or does not contain valid columns."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error("❌ CSV upload failed — %s", str(e), exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
