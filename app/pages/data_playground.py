from fasthtml.common import *
from fasthtml.core import APIRouter
from monsterui.all import *
from monsterui.franken import Grid as Grd
from pages.templates import app_template
from starmodel import State, event
from .components.charts import Apex_Chart, ChartT, construct_script
from pydantic import BaseModel, computed_field
from typing import Dict, List, Any, Optional
import csv
import io
import json
# import pandas as pd  # Not needed for now
from statistics import mean, median, mode
import random
from datetime import datetime, timedelta

rt = APIRouter()

# Sample datasets for immediate demo
SAMPLE_DATASETS = {
    "sales_data": {
        "name": "E-commerce Sales",
        "description": "Monthly sales data across different product categories",
        "data": [
            {"Month": "Jan", "Electronics": 45000, "Clothing": 32000, "Books": 18000, "Category": "Electronics"},
            {"Month": "Feb", "Electronics": 52000, "Clothing": 35000, "Books": 22000, "Category": "Electronics"},
            {"Month": "Mar", "Electronics": 48000, "Clothing": 41000, "Books": 25000, "Category": "Electronics"},
            {"Month": "Apr", "Electronics": 55000, "Clothing": 38000, "Books": 20000, "Category": "Electronics"},
            {"Month": "May", "Electronics": 62000, "Clothing": 45000, "Books": 28000, "Category": "Electronics"},
            {"Month": "Jun", "Electronics": 58000, "Clothing": 42000, "Books": 31000, "Category": "Electronics"},
        ]
    },
    "user_analytics": {
        "name": "User Engagement",
        "description": "Daily active users and engagement metrics",
        "data": [
            {"Date": "2024-01-01", "Daily_Active_Users": 12500, "Session_Duration": 8.5, "Bounce_Rate": 32.1},
            {"Date": "2024-01-02", "Daily_Active_Users": 13200, "Session_Duration": 9.2, "Bounce_Rate": 29.8},
            {"Date": "2024-01-03", "Daily_Active_Users": 11800, "Session_Duration": 7.8, "Bounce_Rate": 35.2},
            {"Date": "2024-01-04", "Daily_Active_Users": 14100, "Session_Duration": 10.1, "Bounce_Rate": 27.5},
            {"Date": "2024-01-05", "Daily_Active_Users": 15300, "Session_Duration": 11.2, "Bounce_Rate": 24.8},
            {"Date": "2024-01-06", "Daily_Active_Users": 13900, "Session_Duration": 9.8, "Bounce_Rate": 28.3},
        ]
    },
    "financial_data": {
        "name": "Stock Performance",
        "description": "Tech stock prices and trading volumes",
        "data": [
            {"Symbol": "TECH", "Price": 125.50, "Volume": 2500000, "Change": 2.3, "Market_Cap": "50B"},
            {"Symbol": "INNO", "Price": 89.75, "Volume": 1800000, "Change": -1.2, "Market_Cap": "35B"},
            {"Symbol": "GROW", "Price": 203.25, "Volume": 3200000, "Change": 4.7, "Market_Cap": "80B"},
            {"Symbol": "STAR", "Price": 156.80, "Volume": 2100000, "Change": 1.8, "Market_Cap": "62B"},
            {"Symbol": "NOVA", "Price": 67.45, "Volume": 1500000, "Change": -0.5, "Market_Cap": "28B"},
        ]
    }
}

class DataPlaygroundState(State):
    """Dynamic state for CSV data visualization with arbitrary fields."""
    
    # Core UI state
    uploaded_filename: str = ""
    total_rows: int = 0
    total_columns: int = 0
    selected_chart_type: str = "bar"
    x_column: str = ""
    y_column: str = ""
    group_column: str = ""
    filter_active: bool = False

    # Data state
    raw_data: List[Dict[str, Any]] = []
    filtered_data: List[Dict[str, Any]] = []
    column_names: List[str] = []
    column_types: Dict[str, str] = {}
    column_stats: Dict[str, Dict[str, Any]] = {}
    
    # Chart state
    chart_title: str = "Data Visualization"
    show_legend: bool = True
    
    # Allow dynamic fields based on CSV columns
    model_config = {"extra": "allow"}
    
    @computed_field
    @property
    def is_data_loaded(self) -> bool:
        return len(self.raw_data) > 0
    
    @computed_field
    @property
    def numeric_columns(self) -> List[str]:
        return [col for col, dtype in self.column_types.items() if dtype in ["numeric", "integer"]]
    
    @computed_field
    @property
    def categorical_columns(self) -> List[str]:
        return [col for col, dtype in self.column_types.items() if dtype in ["categorical", "string"]]
    
    @computed_field
    @property
    def can_create_chart(self) -> bool:
        result = bool(self.x_column and self.y_column and self.is_data_loaded)
        print(f"can_create_chart: {result}, x_column: {self.x_column}, y_column: {self.y_column}, data_loaded: {self.is_data_loaded}")  # Debug
        return result
    
    def detect_column_type(self, values: List[Any]) -> str:
        """Detect the type of a column based on its values."""
        if not values:
            return "unknown"
        
        # Remove None/empty values for analysis
        clean_values = [v for v in values if v is not None and str(v).strip()]
        if not clean_values:
            return "unknown"
        
        # Try to convert to numeric
        numeric_count = 0
        for val in clean_values[:10]:  # Sample first 10 values
            try:
                float(str(val).replace(',', ''))
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        if numeric_count / len(clean_values[:10]) > 0.8:
            # Check if integers
            try:
                all_ints = all(float(str(v).replace(',', '')).is_integer() for v in clean_values[:5])
                return "integer" if all_ints else "numeric"
            except:
                return "numeric"
        
        # Check if dates (simplified without pandas)
        date_count = 0
        for val in clean_values[:5]:
            try:
                # Simple date detection
                val_str = str(val)
                if '-' in val_str or '/' in val_str:
                    datetime.strptime(val_str.replace('/', '-'), '%Y-%m-%d')
                    date_count += 1
            except:
                try:
                    # Try other common date formats
                    datetime.strptime(val_str, '%m/%d/%Y')
                    date_count += 1
                except:
                    pass
        
        if date_count / len(clean_values[:5]) > 0.6:
            return "datetime"
        
        # Check if categorical (limited unique values)
        unique_ratio = len(set(clean_values)) / len(clean_values)
        if unique_ratio < 0.5 and len(set(clean_values)) < 20:
            return "categorical"
        
        return "string"
    
    def calculate_column_stats(self, column: str, values: List[Any]) -> Dict[str, Any]:
        """Calculate statistics for a column."""
        clean_values = [v for v in values if v is not None and str(v).strip()]
        if not clean_values:
            return {"count": 0, "unique": 0}
        
        stats = {
            "count": len(clean_values),
            "unique": len(set(clean_values)),
            "missing": len(values) - len(clean_values)
        }
        
        col_type = self.column_types.get(column, "unknown")
        
        if col_type in ["numeric", "integer"]:
            try:
                numeric_vals = [float(str(v).replace(',', '')) for v in clean_values]
                stats.update({
                    "min": min(numeric_vals),
                    "max": max(numeric_vals),
                    "mean": mean(numeric_vals),
                    "median": median(numeric_vals)
                })
            except:
                pass
        elif col_type == "categorical":
            # Most common values
            from collections import Counter
            counter = Counter(clean_values)
            stats["most_common"] = counter.most_common(3)
        
        return stats
    
    @event
    async def load_sample_data(self, dataset_key: str):
        """Load a sample dataset for immediate demonstration."""
        print(f"Loading sample data: {dataset_key}")  # Debug output
        if dataset_key not in SAMPLE_DATASETS:
            print(f"Dataset key {dataset_key} not found")  # Debug output
            return
        
        dataset = SAMPLE_DATASETS[dataset_key]
        self.raw_data = dataset["data"]
        self.filtered_data = self.raw_data.copy()
        self.uploaded_filename = dataset["name"]
        self.total_rows = len(self.raw_data)
        
        # Extract column information
        if self.raw_data:
            self.column_names = list(self.raw_data[0].keys())
            self.total_columns = len(self.column_names)
            
            # Detect column types and calculate stats
            for col in self.column_names:
                values = [row.get(col) for row in self.raw_data]
                self.column_types[col] = self.detect_column_type(values)
                self.column_stats[col] = self.calculate_column_stats(col, values)
        
        # Auto-select reasonable defaults
        if self.numeric_columns:
            self.y_column = self.numeric_columns[0]
        if self.categorical_columns:
            self.x_column = self.categorical_columns[0]
        elif len(self.column_names) > 1:
            self.x_column = self.column_names[0]
            
        self.chart_title = f"{dataset['name']} Visualization"
        
        print(f"Data loaded successfully: {len(self.raw_data)} rows, {len(self.column_names)} columns")  # Debug
        
        # Update UI
        yield self.data_preview_card()
        yield self.chart_builder_card()
        if self.can_create_chart:
            yield self.visualization_card()
            
        # Hide upload zone
        yield Div(cls="space-y-6 hidden", id="upload-zone-container")
    
    @event
    async def process_csv_upload(self, datastar):
        """Process uploaded CSV using Datastar's native file upload."""
        print(f"Processing CSV upload via Datastar - datastar: {datastar}")  # Debug output
        
        # Extract Datastar file upload signals
        csv_files = datastar.get('csvFiles', [])
        csv_files_names = datastar.get('csvFilesNames', [])
        csv_files_mimes = datastar.get('csvFilesMimes', [])
        
        print(f"csvFiles: {len(csv_files) if csv_files else 0}")
        print(f"csvFilesNames: {csv_files_names}")
        print(f"csvFilesMimes: {csv_files_mimes}")
        
        if not csv_files or not csv_files_names:
            print("No files provided")
            yield Div(
                "No files selected. Please choose a CSV file to upload.",
                cls="alert alert-warning p-4 bg-yellow-100 border border-yellow-300 rounded",
                id="upload-error"
            )
            return
        
        # Get the first file (assuming single file upload)
        file_content_b64 = csv_files[0][0]
        filename = csv_files_names[0][0]
        
        print(f"Processing file: {filename}")
        print(f"Base64 content length: {len(file_content_b64)}")
        
        try:
            # Decode base64 content - remove data URL prefix if present
            import base64
            if file_content_b64.startswith('data:'):
                # Remove data URL prefix (e.g., "data:text/csv;base64,")
                file_content_b64 = file_content_b64.split(',', 1)[1]
            
            csv_content = base64.b64decode(file_content_b64).decode('utf-8')
            print(f"Decoded CSV content length: {len(csv_content)}")
            
            # Process the CSV content
            async for result in self.upload_csv_data(csv_content, filename):
                yield result
            
        except Exception as e:
            print(f"Error processing upload: {str(e)}")
            yield Div(
                f"Error processing file: {str(e)}", 
                cls="alert alert-error p-4 bg-red-100 border border-red-300 rounded",
                id="upload-error"
            )
    
    async def upload_csv_data(self, csv_content: str, filename: str):
        """Process uploaded CSV data and create dynamic state."""
        print(f"Uploading CSV: {filename}, content length: {len(csv_content)}")  # Debug output
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            self.raw_data = list(csv_reader)
            self.filtered_data = self.raw_data.copy()
            self.uploaded_filename = filename
            self.total_rows = len(self.raw_data)
            
            if self.raw_data:
                self.column_names = list(self.raw_data[0].keys())
                self.total_columns = len(self.column_names)
                
                # Detect column types and calculate stats
                for col in self.column_names:
                    values = [row.get(col) for row in self.raw_data]
                    self.column_types[col] = self.detect_column_type(values)
                    self.column_stats[col] = self.calculate_column_stats(col, values)
                    
                    # Dynamically add column data as state attributes
                    setattr(self, f"{col}_data", values)
                
                # Auto-select reasonable defaults
                if self.numeric_columns:
                    self.y_column = self.numeric_columns[0]
                if self.categorical_columns:
                    self.x_column = self.categorical_columns[0]
                elif len(self.column_names) > 1:
                    self.x_column = self.column_names[0]
            
            # Update UI components  
            yield self.data_preview_card()
            yield self.chart_builder_card()
            if self.can_create_chart:
                yield self.visualization_card()
            
            # Hide upload zone
            yield Div(cls="space-y-6 hidden", id="upload-zone-container")
            
        except Exception as e:
            # Handle upload errors
            yield Div(
                f"Error processing CSV: {str(e)}", 
                cls="alert alert-error",
                id="upload-error"
            )
    
    @event
    async def update_chart_settings(self, chart_type: str = None, x_col: str = None, y_col: str = None, group_col: str = None, title: str = None):
        """Update chart configuration and regenerate visualization."""
        if chart_type is not None:
            self.selected_chart_type = chart_type
        if x_col is not None:
            self.x_column = x_col
        if y_col is not None:
            self.y_column = y_col
        if group_col is not None:
            self.group_column = group_col
        if title is not None:
            self.chart_title = title
        
        # Regenerate chart if we have enough data
        if self.can_create_chart:
            yield self.update_chart_script()

    def upload_zone_card(self):
        """File upload interface using Datastar's native file upload."""
        return Card(
            id="upload-zone",
            cls="border-2 border-dashed border-primary/30 hover:border-primary/60 transition-all duration-300"
        )(
            # Datastar file upload with signals and processing
            Div(
                data_signals='{"csvFiles": [], "csvFilesMimes": [], "csvFilesNames": []}',
                cls="py-12 px-8"
            )(
                DivCentered(
                    UkIcon("upload-cloud", cls="w-16 h-16 text-primary/60 mb-4"),
                    H3("Upload Your CSV Data", cls="text-xl font-bold text-foreground mb-2"),
                    P("Select your CSV file to start visualizing data", 
                      cls="text-muted-foreground mb-6"),
                    
                    # Datastar native file input with data-bind
                    Input(
                        type="file",
                        accept=".csv",
                        data_bind="csvFiles",
                        cls="mb-4 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
                    ),
                    
                    # Upload status and process button
                    Div(
                        P("File selected! Click to process.", 
                          cls="text-green-600 text-sm font-medium mb-3"),
                        Button(
                            UkIcon("upload", cls="w-4 h-4 mr-2"),
                            "Process CSV File",
                            data_on_click=DataPlaygroundState.process_csv_upload(),
                            cls="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg"
                        ),
                        data_show="$csvFiles.length > 0",
                        cls="mb-4"
                    ),
                )
            ),
            
            # Sample data options outside the form
            Div(
                    H4("Or try a sample dataset:", cls="text-lg font-semibold text-foreground mb-3 mt-8"),
                    Grid(
                        Card(
                            H5("E-commerce Sales", cls="font-semibold text-foreground mb-2"),
                            P("Monthly sales data across different product categories", cls="text-xs text-muted-foreground mb-4"),
                            Button(
                                "Load Sample Data",
                                data_on_click=DataPlaygroundState.load_sample_data("sales_data"),
                                cls="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg transition-all duration-300 w-full"
                            ),
                            cls="p-4 border hover:shadow-md transition-all duration-300"
                        ),
                        Card(
                            H5("User Analytics", cls="font-semibold text-foreground mb-2"),
                            P("Daily active users and engagement metrics", cls="text-xs text-muted-foreground mb-4"),
                            Button(
                                "Load Sample Data",
                                data_on_click=DataPlaygroundState.load_sample_data("user_analytics"),
                                cls="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg transition-all duration-300 w-full"
                            ),
                            cls="p-4 border hover:shadow-md transition-all duration-300"
                        ),
                        Card(
                            H5("Stock Performance", cls="font-semibold text-foreground mb-2"),
                            P("Tech stock prices and trading volumes", cls="text-xs text-muted-foreground mb-4"),
                            Button(
                                "Load Sample Data",
                                data_on_click=DataPlaygroundState.load_sample_data("financial_data"),
                                cls="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg transition-all duration-300 w-full"
                            ),
                            cls="p-4 border hover:shadow-md transition-all duration-300"
                        ),
                        cols_lg=3, gap=4
                    )
                ),
                cls="py-12 px-8"
            )
    
    def data_preview_card(self):
        """Show preview of loaded data with statistics."""
        if not self.is_data_loaded:
            return Div(id="data-preview")  # Return div with ID even when empty
        
        # Show first few rows
        preview_rows = self.filtered_data[:5]
        
        return Card(
            id="data-preview",
            cls="px-8 animate-fade-in-scale"
        )(
            Div(
                H3("Data Preview", cls="text-xl font-bold text-foreground mb-4"),
            
                # Data table preview
                Div(
                    Table(
                        Thead(
                            Tr(*[Th(col, cls="text-left py-2 px-3 text-sm font-semibold") for col in self.column_names])
                        ),
                        Tbody(
                            *[
                                Tr(
                                    *[Td(str(row.get(col, "")), cls="py-2 px-3 text-sm") for col in self.column_names]
                                )
                                for row in preview_rows
                            ]
                        ),
                        cls="w-full border-collapse"
                    ),
                    cls="overflow-x-auto bg-background rounded-lg border"
                ),
                
                P(f"Showing first 5 of {len(self.filtered_data)} rows", 
                  cls="text-sm text-muted-foreground mt-2 text-center"),                
            )
        )

    def chart_builder_card(self):
        """Interactive chart configuration interface."""
        if not self.is_data_loaded:
            return Div(id="chart-builder")
        
        chart_types = [
            {"value": "bar", "label": "Bar Chart", "icon": "bar-chart"},
            {"value": "line", "label": "Line Chart", "icon": "trending-up"},
            {"value": "area", "label": "Area Chart", "icon": "activity"},
            {"value": "pie", "label": "Pie Chart", "icon": "pie-chart"},
            {"value": "scatter", "label": "Scatter Plot", "icon": "scatter-chart"},
        ]
        
        return Card(
            id="chart-builder",
            cls="px-8 animate-fade-in-scale"
        )(
            H3("Chart Builder", cls="text-xl font-bold text-foreground mb-4"),
            
            Grid(
                # Chart type selection
                Div(
                    H4("Chart Type", cls="text-lg font-semibold text-foreground mb-3"),
                    Grid(
                        *[
                            Button(
                                UkIcon(chart["icon"], cls="w-5 h-5 mb-2"),
                                chart["label"],
                                data_on_click=DataPlaygroundState.update_chart_settings(chart_type=chart["value"]),
                                cls=f"flex flex-col items-center p-3 rounded-lg transition-all duration-300 {'bg-primary text-primary-foreground' if self.selected_chart_type == chart['value'] else 'bg-card hover:bg-muted border'}"
                            )
                            for chart in chart_types
                        ],
                        cols=3, gap=2
                    )
                ),
                
                # Column selection
                Form(
                    H4("Data Mapping", cls="text-lg font-semibold text-foreground mb-3"),
                    
                    # X-axis selection
                    Div(
                        Label("X-Axis (Categories)", cls="text-sm font-medium text-foreground mb-2"),
                        Select(
                            Option("Select column...", value="", selected=not self.x_column),
                            *[
                                Option(col, value=col, selected=self.x_column==col)
                                for col in self.column_names
                            ],
                            name="x_col",
                            cls="w-full p-2 border rounded-lg"
                        ),
                        cls="mb-4"
                    ),
                    
                    # Y-axis selection  
                    Div(
                        Label("Y-Axis (Values)", cls="text-sm font-medium text-foreground mb-2"),
                        Select(
                            Option("Select column...", value="", selected=not self.y_column),
                            *[
                                Option(col, value=col, selected=self.y_column==col)
                                for col in self.numeric_columns
                            ],
                            name="y_col", 
                            cls="w-full p-2 border rounded-lg"
                        ),
                        cls="mb-4"
                    ),
                    
                    # Chart title
                    Div(
                        Label("Chart Title", cls="text-sm font-medium text-foreground mb-2"),
                        Input(
                            type="text",
                            value=self.chart_title,
                            placeholder="Enter chart title",
                            name="title",
                            cls="w-full p-2 border rounded-lg"
                        ),
                        cls="mb-4"
                    ),
                    
                    # Update button
                    Button(
                        "Update Chart",
                        type="submit",
                        cls="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg w-full"
                    ),
                    
                    data_on_submit=DataPlaygroundState.update_chart_settings()
                ),
                
                cols_lg=2, gap=6
            )
        )
    
    def update_chart_script(self):
        """Update the chart script based on the selected chart type."""
        if not self.can_create_chart:
            return Div(
                P("Select X and Y columns to create a visualization", 
                  cls="text-muted-foreground text-center py-8"),
                id="visualization"
            )
        
        
        # Prepare data for chart
        chart_data = self._prepare_chart_data()
        print(f"Chart data prepared: {len(chart_data.get('x_values', []))} points")  # Debug
        
        # Generate chart based on type
        if self.selected_chart_type == "bar":
            chart_script = self._create_bar_chart(chart_data)
        elif self.selected_chart_type == "line":
            chart_script = self._create_line_chart(chart_data)
        elif self.selected_chart_type == "area":
            chart_script = self._create_area_chart(chart_data)
        elif self.selected_chart_type == "pie":
            chart_script = self._create_pie_chart(chart_data)
        else:
            chart_script = self._create_bar_chart(chart_data)  # fallback
        
        return chart_script

    def visualization_card(self, chart_type = None, id="chart-container"):
        """Generate and display the interactive chart."""
        if not self.can_create_chart:
            return Div(
                P("Select X and Y columns to create a visualization", 
                  cls="text-muted-foreground text-center py-8"),
                id="visualization"
            )
        
        # Prepare data for chart
        chart_data = self._prepare_chart_data()
        print(f"Chart data prepared: {len(chart_data.get('x_values', []))} points")  # Debug
        
        ct = chart_type if chart_type else self.selected_chart_type 
        # Generate chart based on type
        if ct == "bar":
            chart_script = self._create_bar_chart(chart_data)
        elif ct == "line":
            chart_script = self._create_line_chart(chart_data)
        elif ct == "area":
            chart_script = self._create_area_chart(chart_data)
        elif ct == "pie":
            chart_script = self._create_pie_chart(chart_data)
        else:
            chart_script = self._create_bar_chart(chart_data)  # fallback

        chart_types = [
            {"value": "bar", "label": "Bar Chart", "icon": "bar-chart"},
            {"value": "line", "label": "Line Chart", "icon": "trending-up"},
            {"value": "area", "label": "Area Chart", "icon": "activity"},
            {"value": "pie", "label": "Pie Chart", "icon": "pie-chart"},
            {"value": "scatter", "label": "Scatter Plot", "icon": "scatter-chart"},
        ]
        
        return Card(
            id="visualization",
            cls="px-8 animate-fade-in-scale"
        )(
            H3(self.chart_title, cls="text-xl font-bold text-foreground mb-4"),
            Div(
                Apex_Chart(
                    chart_script,
                    cls="min-h-96"
                ),
                id=id,
                cls="min-h-96"
            ),
            Grid(
                *[
                    Button(
                        UkIcon(chart["icon"], cls="w-5 h-5 mb-2"),
                        chart["label"],
                        data_on_click=DataPlaygroundState.update_chart_settings(chart_type=chart["value"]),
                        cls="p-3 transition-all duration-300",
                        data_class=f"{{'bg-primary text-primary-foreground': {DataPlaygroundState.selected_chart_type_signal} === '{chart['value']}', 'bg-card hover:bg-muted border': {DataPlaygroundState.selected_chart_type_signal} !== '{chart['value']}'}}"
                    )
                    for chart in chart_types
                ],
                cols=3, gap=2
            ),
            
            # Chart info
            Div(
                P(f"Showing {len(self.filtered_data)} data points", cls="text-sm text-muted-foreground"),
                P(f"X: {self.x_column} | Y: {self.y_column}", cls="text-sm text-muted-foreground"),
                cls="mt-4 text-center space-y-1 bg-muted/30 p-3 rounded-lg"
            )
        )
    
    def _prepare_chart_data(self) -> Dict[str, Any]:
        """Prepare data for chart visualization."""
        if not self.filtered_data:
            return {}
        
        # Extract x and y values
        x_values = []
        y_values = []
        
        for row in self.filtered_data:
            x_val = row.get(self.x_column, "")
            y_val = row.get(self.y_column, 0)
            
            # Clean and convert y values
            try:
                if isinstance(y_val, str):
                    y_val = float(y_val.replace(',', ''))
                else:
                    y_val = float(y_val)
            except (ValueError, TypeError):
                y_val = 0
            
            x_values.append(str(x_val))
            y_values.append(y_val)
        
        return {
            "x_values": x_values,
            "y_values": y_values,
            "x_column": self.x_column,
            "y_column": self.y_column
        }
    
    def _create_bar_chart(self, data: Dict[str, Any], id="bar-chart") -> Script:
        """Create a bar chart visualization."""
        return construct_script(
            chart_type=ChartT.bar,
            series=[{
                "name": data["y_column"],
                "data": data["y_values"]
            }],
            categories=data["x_values"],
            colors=["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--chart-5))"],
            id=id 
        )
    
    def _create_line_chart(self, data: Dict[str, Any], id="line-chart") -> Script:
        """Create a line chart visualization."""
        return construct_script(
            chart_type=ChartT.line,
            series=[{
                "name": data["y_column"],
                "data": data["y_values"]
            }],
            categories=data["x_values"],
            id=id
        )
    
    def _create_area_chart(self, data: Dict[str, Any], id="area-chart") -> Script:
        """Create an area chart visualization."""
        return construct_script(
            chart_type=ChartT.area,
            series=[{
                "name": data["y_column"],
                "data": data["y_values"]
            }],
            categories=data["x_values"],
            fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
            id=id
        )
    
    def _create_pie_chart(self, data: Dict[str, Any], id="pie-chart") -> Script:
        """Create a pie chart visualization."""
        # For pie charts, aggregate data by x values
        from collections import defaultdict
        aggregated = defaultdict(float)
        
        for x, y in zip(data["x_values"], data["y_values"]):
            aggregated[x] += y
        
        labels = list(aggregated.keys())
        values = list(aggregated.values())
        
        return construct_script(
            chart_type=ChartT.pie,
            series=values,
            labels=labels,
            id=id
        )    

@rt("/data-playground")
@app_template("Data Visualization Playground")
def data_playground(request):
    """Interactive CSV data visualization playground."""
    state = DataPlaygroundState.get(request)
    
    return Div(cls="space-y-6")(
        state,
        
        # Page header
        DivCentered(
            H1("📊 Data Visualization Playground", cls="text-4xl font-bold text-foreground mb-4"),
            P("Upload your CSV data and create stunning visualizations in real-time", 
              cls="text-xl text-muted-foreground mb-8 max-w-3xl text-center"),                        
        ),
        # Upload zone (always present, but hidden when data is loaded)
        Div(
            state.upload_zone_card(),
            id="upload-zone-container",
            cls="space-y-6" + (" hidden" if state.is_data_loaded else ""),
            data_show=f"{DataPlaygroundState.is_data_loaded_signal} === false"
        ),
        # Main content area
        TabContainer(
            Li(A("Visualization", cls="uk-active")),
            Li(A("Data Preview")),
            Li(A("Chart Builder")),
            uk_switcher="connect: #component-nav; animation:uk-anmt-fade",
            data_show=f"{DataPlaygroundState.is_data_loaded_signal}"
            # alt=True,
        ),
        Ul(id="component-nav", cls="uk-switcher max-w-7xl mx-auto")(
            Li(cls="flex flex-row gap-4")(
                state.visualization_card(),
                state.visualization_card(chart_type="pie", id="chart-container-pie")
            ),        
            Li(state.data_preview_card()),
            Li(state.chart_builder_card()),
            data_show=f"{DataPlaygroundState.is_data_loaded_signal}"
        ),
        id="content"
    )