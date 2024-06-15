
from django.shortcuts import render
import pandas as pd
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.db import connection

def export_pdf(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SET @initial_amount := 0;
            SET @cumulative_received := 0;
        """)

        # Main query to calculate initial_amount, cumulative_received, and select other fields
        cursor.execute("""
            SELECT 
                Stage_name,
                due_date,
                IF(initial_amount = 0, total_paid_amount, initial_amount) AS initial_amount,  -- Check if initial_amount is 0 and replace it with total_paid_amount
                IFNULL(received_date, CURDATE()) AS received_date,  -- Replace NULL received_date with current date
                IFNULL(received_amount, 0) AS received_amount,  -- Replace NULL received_amount with 0
                customer_receipt_type,
                date_difference,
                10.25 AS interest_per,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) AS Interest_percentage,
                ROUND((((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_18_percent,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365) + (((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_gst
            FROM (
                -- Subquery to fetch data and calculate initial_amount, cumulative_received, and retrieve receipt_id
                SELECT 
                    Stage_name,
                    due_date,
                    total_paid_amount,
                    received_date,
                    customer_receipt_type,
                    received_amount,
                    date_difference,
                    -- Calculate initial_amount and update @cumulative_received
                    @initial_amount := IF(rn = 1, total_paid_amount, @initial_amount - @cumulative_received) AS initial_amount,
                    @cumulative_received := received_amount AS cumulative_received
                FROM (
                    -- Inner query to join tables and calculate necessary fields, sorting received_amount based on reference_master id
                    SELECT 
                        ps.Stage_name,
                        ps.due_date,
                        ps.total_paid_amount,
                        md.recieved_date AS received_date,
                        md.customer_receipt_tpye AS customer_receipt_type,
                        rm.amount AS received_amount,
                        -- Calculate date_difference with condition
                        CASE WHEN ps.due_date > md.recieved_date THEN 0
                             ELSE ABS(DATEDIFF(ps.due_date, md.recieved_date))
                        END AS date_difference,
                        ROW_NUMBER() OVER (PARTITION BY ps.Stage_name ORDER BY ps.due_date, md.recieved_date, rm.id) AS rn
                    FROM 
                        payment_schedule_tablename AS ps
                    LEFT JOIN 
                        reference_master_table AS rm ON ps.id = rm.object_id OR (rm.object_id IS NULL AND rm.against = 'Advance')
                    LEFT JOIN 
                        master_table AS md ON md.id = rm.receipt_id
                    -- Ensure proper ordering within the subquery
                    ORDER BY 
                        ps.Stage_name, ps.due_date, md.recieved_date, rm.id
                ) AS subquery
            ) AS final_query
            -- Outer ordering as per your requirement
            ORDER BY 
                Stage_name, due_date, received_date
        """)

        rows = cursor.fetchall()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="table.pdf"'

    # Define a custom page size
    custom_page_width = 1070  # in points (1 inch = 72 points)
    custom_page_height = 600  # in points

    p = canvas.Canvas(response, pagesize=(custom_page_width, custom_page_height))

    # Add title in the middle of the page
    p.setFont("Helvetica-Bold", 14)
    title_text = "Interest Report"
    title_width = p.stringWidth(title_text, "Helvetica-Bold", 14)
    p.drawString((custom_page_width - title_width) / 2, custom_page_height - 50, title_text)

    # Adjust starting point for the table
    table_start_x = 20
    table_start_y = custom_page_height - 90

    data = [
        ['Description', 'Due Date', 'Due Amount', 'Received Date', 'Paid Amount','Receipt Type', 'No of days', 'Interest %', 'Interest', 'GST @ 18%', 'Total Interest'],
        *rows
    ]

    # Define table settings
    column_widths = [180, 80, 80, 80, 80, 80, 60, 80, 80, 80, 80]
    row_height = 20
    header_row_height = 25
    padding = 10

    # Draw table headers with outlines and lines
    p.setFont("Helvetica-Bold", 10)
    for i, header in enumerate(data[0]):
        p.rect(table_start_x + sum(column_widths[:i]) + padding, table_start_y - header_row_height + padding, column_widths[i], header_row_height, stroke=1, fill=0)
        p.drawString(table_start_x + sum(column_widths[:i]) + padding + 2, table_start_y - header_row_height + padding + 5, header)

    # Adjust table_start_y for space between header and data
    table_start_y -= header_row_height + padding

    # Draw table rows with outlines and lines
    p.setFont("Helvetica", 10)
    for row_index, row in enumerate(data[1:], start=1):
        table_start_y -= row_height
        for col_index, cell in enumerate(row):
            # Draw rectangle outline
            p.rect(table_start_x + sum(column_widths[:col_index]) + padding, table_start_y, column_widths[col_index], row_height, stroke=1, fill=0)
            # Draw cell content
            if isinstance(cell, str):
                lines = text_wrap(cell, p, column_widths[col_index], row_height, max_words=3)
                for line_index, line in enumerate(lines):
                    p.drawString(table_start_x + sum(column_widths[:col_index]) + padding + 2, table_start_y + padding - line_index * row_height, line)
            else:
                p.drawString(table_start_x + sum(column_widths[:col_index]) + padding + 2, table_start_y + padding, str(cell))

        # Draw horizontal lines between rows
        p.setLineWidth(0.2)
        p.line(table_start_x, table_start_y, table_start_x + sum(column_widths) + padding, table_start_y)

        # Check if the row height exceeds the page height, then create a new page
        if table_start_y <= 50 and row_index < len(data) - 1:
            p.showPage()
            table_start_y = custom_page_height - 50
            table_start_y -= header_row_height

    p.showPage()
    p.save()

    return response

def text_wrap(text, canvas, max_width, max_height, max_words=3):
    lines = []
    if canvas.stringWidth(text) <= max_width:
        lines.append(text)
    else:
        line = ''
        words = text.split()
        for word in words:
            if len(line.split()) < max_words:
                if canvas.stringWidth(line + ' ' + word) <= max_width:
                    line += ' ' + word
                else:
                    lines.append(line)
                    line = word
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)

    # Combine wrapped lines into a single list item
    combined_lines = []
    current_line = ''
    for line in lines:
        if canvas.stringWidth(current_line + ' ' + line) <= max_width:
            current_line += ' ' + line
        else:
            combined_lines.append(current_line.strip())
            current_line = line.strip()

    if current_line:
        combined_lines.append(current_line.strip())

    return combined_lines


def export_excel(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SET @initial_amount := 0;
            SET @cumulative_received := 0;
        """)

        # Main query to calculate initial_amount, cumulative_received, and select other fields
        cursor.execute("""
            SELECT 
                Stage_name,
                due_date,
                IF(initial_amount = 0, total_paid_amount, initial_amount) AS initial_amount,  -- Check if initial_amount is 0 and replace it with total_paid_amount
                IFNULL(received_date, CURDATE()) AS received_date,  -- Replace NULL received_date with current date
                IFNULL(received_amount, 0) AS received_amount,  -- Replace NULL received_amount with 0
                customer_receipt_type,
                date_difference,
                10.25 AS interest_per,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) AS Interest_percentage,
                ROUND((((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_18_percent,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365) + (((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_gst
            FROM (
                -- Subquery to fetch data and calculate initial_amount, cumulative_received, and retrieve receipt_id
                SELECT 
                    Stage_name,
                    due_date,
                    total_paid_amount,
                    received_date,
                    customer_receipt_type,
                    received_amount,
                    date_difference,
                    -- Calculate initial_amount and update @cumulative_received
                    @initial_amount := IF(rn = 1, total_paid_amount, @initial_amount - @cumulative_received) AS initial_amount,
                    @cumulative_received := received_amount AS cumulative_received
                FROM (
                    -- Inner query to join tables and calculate necessary fields, sorting received_amount based on reference_master id
                    SELECT 
                        ps.Stage_name,
                        ps.due_date,
                        ps.total_paid_amount,
                        md.recieved_date AS received_date,
                        md.customer_receipt_tpye AS customer_receipt_type,
                        rm.amount AS received_amount,
                        -- Calculate date_difference with condition
                        CASE WHEN ps.due_date > md.recieved_date THEN 0
                             ELSE ABS(DATEDIFF(ps.due_date, md.recieved_date))
                        END AS date_difference,
                        ROW_NUMBER() OVER (PARTITION BY ps.Stage_name ORDER BY ps.due_date, md.recieved_date, rm.id) AS rn
                    FROM 
                        payment_schedule_tablename AS ps
                    LEFT JOIN 
                        reference_master_table AS rm ON ps.id = rm.object_id OR (rm.object_id IS NULL AND rm.against = 'Advance')
                    LEFT JOIN 
                        master_table AS md ON md.id = rm.receipt_id
                    -- Ensure proper ordering within the subquery
                    ORDER BY 
                        ps.Stage_name, ps.due_date, md.recieved_date, rm.id
                ) AS subquery
            ) AS final_query
            -- Outer ordering as per your requirement
            ORDER BY 
                Stage_name, due_date, received_date
        """)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=columns)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="table.xlsx"'

    # Write DataFrame to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        # Adjust column widths
        worksheet = writer.sheets['Sheet1']
        for idx, col in enumerate(df):
            max_length = df[col].astype(str).map(len).max()
            max_length = max(max_length, len(col)) + 2  # Adding space
            worksheet.column_dimensions[chr(65 + idx)].width = max_length

    return response


def fetch_data(request):
    with connection.cursor() as cursor:
        # Initialize variables
        cursor.execute("""
            SET @initial_amount := 0;
            SET @cumulative_received := 0;
        """)

        # Main query to calculate initial_amount, cumulative_received, and select other fields
        cursor.execute("""
            SELECT 
                Stage_name,
                due_date,
                IF(initial_amount = 0, total_paid_amount, initial_amount) AS initial_amount,  -- Check if initial_amount is 0 and replace it with total_paid_amount
                IFNULL(received_date, CURDATE()) AS received_date,  -- Replace NULL received_date with current date
                IFNULL(received_amount, 0) AS received_amount,  -- Replace NULL received_amount with 0
                customer_receipt_type,
                date_difference,
                10.25 AS interest_per,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) AS Interest_percentage,
                ROUND((((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_18_percent,
                ROUND(((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365) + (((IFNULL(received_amount, 0) * ABS(date_difference) * 10.25 / 100) / 365)) * 0.18) AS calculated_interest_gst
            FROM (
                -- Subquery to fetch data and calculate initial_amount, cumulative_received, and retrieve receipt_id
                SELECT 
                    Stage_name,
                    due_date,
                    total_paid_amount,
                    received_date,
                    customer_receipt_type,
                    received_amount,
                    date_difference,
                    -- Calculate initial_amount and update @cumulative_received
                    @initial_amount := IF(rn = 1, total_paid_amount, @initial_amount - @cumulative_received) AS initial_amount,
                    @cumulative_received := received_amount AS cumulative_received
                FROM (
                    -- Inner query to join tables and calculate necessary fields, sorting received_amount based on reference_master id
                    SELECT 
                        ps.Stage_name,
                        ps.due_date,
                        ps.total_paid_amount,
                        md.recieved_date AS received_date,
                        md.customer_receipt_tpye AS customer_receipt_type,
                        rm.amount AS received_amount,
                        -- Calculate date_difference with condition
                        CASE WHEN ps.due_date > md.recieved_date THEN 0
                             ELSE ABS(DATEDIFF(ps.due_date, md.recieved_date))
                        END AS date_difference,
                        ROW_NUMBER() OVER (PARTITION BY ps.Stage_name ORDER BY ps.due_date, md.recieved_date, rm.id) AS rn
                    FROM 
                        payment_schedule_tablename AS ps
                    LEFT JOIN 
                        reference_master_table AS rm ON ps.id = rm.object_id OR (rm.object_id IS NULL AND rm.against = 'Advance')
                    LEFT JOIN 
                        master_table AS md ON md.id = rm.receipt_id
                    -- Ensure proper ordering within the subquery
                    ORDER BY 
                        ps.Stage_name, ps.due_date, md.recieved_date, rm.id
                ) AS subquery
            ) AS final_query
            -- Outer ordering as per your requirement
            ORDER BY 
                Stage_name, due_date, received_date
        """)

        # Fetch all rows
        rows = cursor.fetchall()

    # Define the context for the template
    context = {
        'data': rows,
    }

    # Render the template with the context
    return render(request, 'home.html', context)


