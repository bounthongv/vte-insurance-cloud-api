from flask import Flask, request, Response
import pyodbc
import json
import os

# Flask app
app = Flask(__name__)

# Retrieve database configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
DB_PORT = os.getenv("DB_PORT", "14661")
DB_USER = os.getenv("DB_USER", "taxapi")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2024.com")
DB_NAME = os.getenv("DB_NAME", "TaxAPI")

def get_db_connection():
    """Establish a connection to the MSSQL database."""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD}"
    )
    return pyodbc.connect(connection_string)

@app.route('/loadInvoices', methods=['GET'])
def get_invoices():
    """Fetch invoices and their details from the database."""
    inv_no = request.args.get('inv_no')  # Optional query parameter

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch parent records from TaxInv
        if inv_no:
            parent_query = "SELECT * FROM TaxInv WHERE inv_no = ?"
            cursor.execute(parent_query, (inv_no,))
        else:
            parent_query = "SELECT * FROM TaxInv"
            cursor.execute(parent_query)

        parent_rows = cursor.fetchall()

        if not parent_rows:
            return Response(json.dumps({"error": "No invoices found."}, ensure_ascii=False),
                            content_type="application/json; charset=utf-8", status=404)

        invoices = []

        for parent in parent_rows:
            # Map parent fields to a dictionary
            invoice = {
                "INV_NO": parent.inv_no,
                "SALE_CNT": parent.sale_cnt,
                "SUPL_AMT": parent.supl_amt,
                "VAT_AMT": parent.vat_amt,
                "SALE_AMT": parent.sale_amt,
                "SALE_AMT_WORD": parent.sale_amt_word,
                "DISC_AMT":parent.disc_amt,
                "CUST_TIN": parent.cust_tin,
                "CUST_FULL_NM": parent.cust_full_nm,
                "CUST_ADDR": parent.cust_addr,
                "CUST_TEL": parent.cust_tel,
                "CUST_ACCNO": parent.cust_accno,
                "CUST_ACCNAM": parent.cust_accnam,
                "PAY_TYPE": parent.pay_type,
                "ODER_NO": parent.order_no,
                "STATUS": parent.status,
                "FAIL_REASON": parent.fail_reason,
                "CREATE_DATE": parent.create_date,
                "UPDATE_DATE": parent.update_date,
                "ORDER_TYPE": parent.order_type,
                "INV_DETAIL": []  # Placeholder for child records
            }

            # Fetch child records from TaxInvDetail
            child_query = "SELECT * FROM TaxInvDetail WHERE inv_no = ?"
            cursor.execute(child_query, (parent.inv_no,))
            child_rows = cursor.fetchall()

            for child in child_rows:
                invoice["INV_DETAIL"].append({
                    "INV_DT_ID": child.inv_dt_id,
                    "INV_NO": child.inv_no,
                    "PROD_CD": child.prod_cd,
                    "PROD_NM": child.prod_nm,
                    "SALE_CNT": child.sale_cnt,
                    "UNIT_SALE": child.unit_sale,
                    "UNIT_SALE_AMT": child.unit_sale_amt,
                    "VAT_AMT": child.vat_amt,
                    "SALE_AMT": child.sale_amt
                })

            invoices.append(invoice)

        # Return response as JSON without escaping non-ASCII characters
        response_json = json.dumps(invoices, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8"), 200

    except Exception as e:
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8"), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/uploadInvoice', methods=['POST'])
def upload_invoice():
    """Insert invoice data into the database."""
    try:
        # Parse the JSON payload
        data = request.get_json()
        if not data:
            return Response(
                json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Validate required fields
        required_fields = ["keyCode", "signDate", "ORDER_NO"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                json.dumps({"error": f"Missing required field(s): {', '.join(missing_fields)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        if data["keyCode"] != "VTI":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract invoice object
        inv = data.get("INV")
        if not inv:
            return Response(
                json.dumps({"error": "Missing 'INV' object in payload"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        inv_no = inv.get("INV_NO")
        if not inv_no:
            return Response(
                json.dumps({"error": "Missing 'INV_NO' in 'INV' object"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract ORDER_NO from the root of the JSON payload
        order_no = data["ORDER_NO"]  # Only fetch it once

        if not inv:
            return Response(
                json.dumps({"error": "Missing 'INV' object in payload"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into the parent table
        taxinv_query = """
            INSERT INTO Taxinv (inv_no, sale_cnt, supl_amt, vat_amt, sale_amt, disc_amt, cust_tin, cust_full_nm, 
                        cust_addr, cust_tel, cust_accno, cust_accnam, pay_type, order_no, status, 
                        create_date,  update_date, order_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        taxinv_params = (
            inv["INV_NO"], inv["SALE_CNT"], inv["SUPL_AMT"], inv["VAT_AMT"], inv["SALE_AMT"], inv["DISC_AMT"],
            inv["CUST_TIN"], inv["CUST_FULL_NM"], inv["CUST_ADDR"],
            inv["CUST_TEL"], inv["CUST_ACCNO"], inv["CUST_ACCNAM"],
            inv["PAY_TYPE"], order_no, inv["STATUS"], inv["CREATE_DATE"], inv["UPDATE_DATE"],
            inv["ORDER_TYPE"]
        )
        cursor.execute(taxinv_query, taxinv_params)

        # Insert into the child table
        inv_detail_query = """
            INSERT INTO TaxinvDetail (inv_no, prod_cd, prod_nm, sale_cnt, 
                                      unit_sale, unit_sale_amt, vat_amt, sale_amt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for detail in inv["INV_DETAIL"]:
            inv_detail_params = (
                inv_no,  # Use the inv_no extracted from the INV object
                detail["PROD_CD"],
                detail["PROD_NM"], detail["SALE_CNT"], detail["UNIT_SALE"],
                detail["UNIT_SALE_AMT"], detail["VAT_AMT"], detail["SALE_AMT"]
            )
            cursor.execute(inv_detail_query, inv_detail_params)

        # Commit the transaction
        conn.commit()

        return Response(
            json.dumps({"code": "200", "message": "Invoice uploaded successfully"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )

    except Exception as e:
        # Handle errors
        return Response(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=500
        )

    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    app.run(debug=False)
