from flask import Flask, request, Response, jsonify
import pyodbc
import json
import os
import hashlib
from datetime import datetime

# Flask app
app = Flask(__name__)

# Define the decorator at the top
#stored_token = os.getenv("BEARER_TOKEN")
# I have saved earleir with different name
stored_token = os.getenv("API_TOKEN")

def token_required(f):
    """Decorator to protect routes with Bearer Token Authentication."""
    def wrapper(*args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        
        # Check if the Authorization header is provided and in the correct format
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        
        # Extract the token
        token = auth_header.split(" ")[1]
        
        # Compare the provided token with the stored token
        if token != stored_token:
            return jsonify({"msg": "Invalid token"}), 401
        
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__  # Preserve the name of the original function
    return wrapper




# Retrieve database configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
DB_PORT = os.getenv("DB_PORT", "14661")
DB_USER = os.getenv("DB_USER", "taxapi")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2024.com")
DB_NAME = os.getenv("DB_NAME", "TaxAPI")

# Secret key for HMAC signing (this should be stored securely)
# SECRET_KEY = os.getenv('SECRET_KEY')


def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date, order_no):
    """Generate a signature using keyCode, signDate, and ORDER_NO."""
    concatenated = f"{key_code}{sign_date}{order_no}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

def generate_signature_apis(key_code, sign_date):
    """Generate a signature using keyCode, signDate"""
    concatenated = f"{key_code}{sign_date}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

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
@token_required  # Add this line to protect the route
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
                "CUST_ID": parent.cust_id,
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
@token_required  # Add this line to protect the route
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


        # Extract fields from the request
        key_code = data["keyCode"]
        sign_date = data["signDate"]
        order_no = data["ORDER_NO"]

        client_signature = data["signature"]

        # Generate the string to sign
        string_to_sign = f"{key_code}{sign_date}{order_no}"

        # Calculate the server's signature using HMAC
        server_signature = generate_signature(key_code, sign_date, order_no)


        # Compare the client signature with the server's signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Verify if the client's signature matches the server's signature
        #if not hmac.compare_digest(server_signature, client_signature):
        #    return Response(
        #        json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
        #        content_type="application/json; charset=utf-8",
        #        status=400
        #    )

        # Extract invoice object
        inv = data.get("INV")
        if not inv:
            return Response(
                json.dumps({"error": "Missing 'INV' object in payload"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # remove 6-1-25, invoice number will be update by apis, not upload by vti
        # inv_no = inv.get("INV_NO")
        # if not inv_no:
        #     return Response(
        #         json.dumps({"error": "Missing 'INV_NO' in 'INV' object"}, ensure_ascii=False),
        #         content_type="application/json; charset=utf-8",
        #         status=400
        #     )

        # Extract ORDER_NO from the root of the JSON payload
        order_no = data["ORDER_NO"]  # Only fetch it once

        if not inv:
            return Response(
                json.dumps({"error": "Missing 'INV' object in payload"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

         # Insert defaults for missing dates
        inv_status = "wait"
        create_date = None  # Placeholder for database GETDATE()
        update_date = None  # Leave as NULL


        validation_errors = []
        
        # Required field validations
        # if not inv.get("INV_NO"):
            # validation_errors.append({"code": 10001, "message": "Invoice number cannot be empty."})
        if not inv.get("SALE_CNT") or inv.get("SALE_CNT") <= 0:
            validation_errors.append({"code": 10002, "message": "Sale count cannot be zero or null."})
        if not inv.get("SUPL_AMT") or inv.get("SUPL_AMT") <= 0:
            validation_errors.append({"code": 10003, "message": "Supplier amount cannot be zero or null."})

        # remove 5-1-2025, chinese says should allo 0, or blank
        # if not inv.get("VAT_AMT") or inv.get("VAT_AMT") <= 0:
        #     validation_errors.append({"code": 10004, "message": "VAT amount cannot be zero or null."})

        if not inv.get("SALE_AMT") or inv.get("SALE_AMT") <= 0:
            validation_errors.append({"code": 10005, "message": "Sale amount cannot be zero or null."})
        if not inv.get("CUST_FULL_NM"):
            validation_errors.append({"code": 10006, "message": "Customer full name cannot be empty."})
        if not inv.get("PAY_TYPE"):
            validation_errors.append({"code": 10007, "message": "Payment type cannot be empty."})
        #if not inv.get("CREATE_DATE"):
        #    validation_errors.append({"code": 10008, "message": "Create date cannot be empty."})
        if not inv.get("ORDER_TYPE"):
            validation_errors.append({"code": 10009, "message": "Order type cannot be empty."})
        if not inv.get("CUST_ID"):
            validation_errors.append({"code": 10004, "message": "Custmoer ID cannot be empty."})
        

        # Validation rules for required fields and allowed values
        allowed_order_types = ["insert", "update", "delete", "cancel"]
        allowed_status = ["wait", "success", "fail","cancel"]
        allowed_payment_types = ["cash", "transfer", "cheque"]

        if inv.get("ORDER_TYPE") and inv["ORDER_TYPE"] not in allowed_order_types:
            validation_errors.append({"code": 10010, "message": f"Order type must be one of {', '.join(allowed_order_types)}."})
        if inv.get("STATUS") and inv["STATUS"] not in allowed_status:
            validation_errors.append({"code": 10011, "message": f"Status must be one of {', '.join(allowed_status)}."})
        if inv.get("PAY_TYPE") and inv["PAY_TYPE"] not in allowed_payment_types:
            validation_errors.append({"code": 10012, "message": f"Payment type must be one of {', '.join(allowed_payment_types)}."})
       
        
        # Status is assigned directly as "wait" so no validation is needed, but still I put it , may be we 
        # we will modify for further to freely input status

        # If there are validation errors, return a 400 response with all issues
        if validation_errors:
            return Response(
                json.dumps({"error": validation_errors}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into the parent table with update_date set to the same as create_date
        taxinv_query = """
            INSERT INTO Taxinv (sale_cnt, supl_amt, fee_amt, vat_amt, sale_amt, disc_amt, cust_tin, cust_id, cust_full_nm, 
                                cust_addr, cust_tel, bank_name, cust_accno, cust_accnam, pay_type, bill_type, pay_bank, agency_fee, order_no, status, 
                                create_date, update_date, order_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), ?)
        """
        taxinv_params = (
            inv["SALE_CNT"], inv["SUPL_AMT"], inv["FEE_AMT"], inv["VAT_AMT"], inv["SALE_AMT"], inv.get("DISC_AMT", 0),
            inv.get("CUST_TIN"), inv.get("CUST_ID"), inv.get("CUST_FULL_NM"), inv.get("CUST_ADDR"), inv.get("CUST_TEL"), inv.get("BANK_NAME"),
            inv.get("CUST_ACCNO"), inv.get("CUST_ACCNAM"), inv.get("PAY_TYPE"), inv.get("BILL_TYPE"), inv.get("PAY_BANK"), inv.get("AGENCY_FEE"), order_no, inv_status, inv.get("ORDER_TYPE")
        )

        cursor.execute(taxinv_query, taxinv_params)

        # Insert into the child table
        inv_detail_query = """
            INSERT INTO TaxinvDetail (order_no, prod_cd, prod_nm, sale_cnt, 
                                      unit_sale, unit_sale_amt, vat_amt, sale_amt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for detail in inv["INV_DETAIL"]:
            inv_detail_params = (
                order_no,  # Use the order_no extracted from the INV object
                detail["PROD_CD"],
                detail["PROD_NM"], detail["SALE_CNT"], detail["UNIT_SALE"],
                detail["UNIT_SALE_AMT"], detail["VAT_AMT"], detail["SALE_AMT"]
            )
            cursor.execute(inv_detail_query, inv_detail_params)

        # Commit the transaction
        conn.commit()

        
        # Fetch the CREATE_DATE and UPDATE_DATE after the insert
        fetch_query = """
            SELECT create_date, update_date FROM Taxinv WHERE order_no = ?
        """
        cursor.execute(fetch_query, (order_no,))
        result = cursor.fetchone()

        # Convert SQL Server default datetime format to the desired format
        if result:
            create_date = datetime.strptime(str(result[0]), "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
            update_date = datetime.strptime(str(result[1]), "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
        else:
            raise Exception("Failed to retrieve timestamps for the inserted order.")
       

        # Include timestamps in the response
        return Response(
            json.dumps({
                "code": "200",
                "data": {
                    "ORDER_NO": order_no,
                    "CREATE_DATE": create_date,
                    "UPDATE_DATE": update_date
                },
                "message": "Order uploaded successfully"
            }, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )
# Return success response with the specified structure
        # return Response(
        #     json.dumps({
        #         "code": "200",
        #         "data": {
        #             "ORDER_NO": order_no,
                
        #         },
        #         "message": "Order uploaded successfully"
        #     }, ensure_ascii=False),
        #     content_type="application/json; charset=utf-8",
        #     status=200
        # )
        
    # except pyodbc.IntegrityError as e:
    # # Handle database integrity errors for duplicates
    #     if "duplicate key" in str(e).lower():
    #         if "order_no" in str(e).lower():
    #             error_code = 20001
    #             error_message = "Duplicate ORDER_NO detected."
    #         elif "inv_no" in str(e).lower():
    #             error_code = 20002
    #             error_message = "Duplicate INV_NO detected."
    #         else:
    #             error_code = 20000
    #             error_message = "Database integrity error."
            
    #         return Response(
    #             json.dumps({"error": {"code": error_code, "message": error_message}}, ensure_ascii=False),
    #             content_type="application/json; charset=utf-8",
    #             status=400
    #         )

    except pyodbc.IntegrityError as e:
        # Handle database integrity errors for duplicates
        error_message = str(e).lower()
        if "order_no" in error_message:
            error_code = 20001
            user_message = "Duplicate ORDER_NO detected."
        # elif "inv_no" in error_message:
        #     error_code = 20002
        #     user_message = "Duplicate INV_NO detected."
        else:
            error_code = 20000
            user_message = "Database integrity error (Possible duplicated ORDER_NO)"

        return Response(
            json.dumps({
                "error": {
                    "code": error_code,
                    "message": user_message
                }
            }, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=400
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


@app.route('/getInvoiceStatus', methods=['POST'])
@token_required  # Add this line to protect the route
def get_invoice_status():
    """Check the processing status of a previously uploaded invoice."""
    try:
         # Parse the JSON payload
        data = request.get_json()
        if not data:
            return Response(
                json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Parse query parameters
        key_code = data["keyCode"]
        sign_date = data["signDate"]
        order_no = data["ORDER_NO"]

        client_signature = data["signature"]

        # Validate required parameters
        if not all([order_no, key_code, sign_date, client_signature]):
            return Response(
                json.dumps({"error": "Missing required parameters: ORDER_NO, keyCode, signDate, or sign"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Validate keyCode
        if key_code != "VTI":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        server_signature = generate_signature(key_code, sign_date, order_no)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch invoice status
        query = """
            SELECT inv_no, order_no, status, order_type, sale_amt_word, fail_reason, update_date
            FROM TaxInv
            WHERE order_no = ?
        """
        cursor.execute(query, (order_no,))
        invoice = cursor.fetchone()

        if not invoice:
            return Response(
                json.dumps({"error": "No invoice found for the provided ORDER_NO."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        formated_update_date = datetime.strptime(invoice.update_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
        
        # Map query result to a dictionary
        result = {
            "ORDER_NO": invoice.order_no,
            "INV_NO": invoice.inv_no,
            "STATUS": invoice.status,
            "ORDER_TYPE": invoice.order_type,
            "SALE_AMT_WORD": invoice.sale_amt_word,
            "FAIL_REASON": invoice.fail_reason or "",
            "UPDATE_DATE": formated_update_date
        }

        # Return the response
        response_json = json.dumps({
            "code": "200",
            "data": result,
            "message": "Invoice status retrieved successfully"
        }, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=200)

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()


@app.route('/cancelInvoice', methods=['PATCH'])
@token_required  # Add this line to protect the route
def cancel_invoice():
    """Cancel an existing invoice in the system."""
    try:
        # Parse the JSON payload
        data = request.get_json()
        if not data:
            return Response(
                json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract required parameters
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        order_no = data.get("ORDER_NO")
        client_signature = data.get("signature")

        # Validate required parameters
        if not all([order_no, key_code, sign_date, client_signature]):
            return Response(
                json.dumps({"error": "Missing required parameters: ORDER_NO, keyCode, signDate, or signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Validate keyCode
        if key_code != "VTI":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        server_signature = generate_signature(key_code, sign_date, order_no)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to check if the invoice exists
        check_query = "SELECT status FROM TaxInv WHERE order_no = ?"
        cursor.execute(check_query, (order_no,))
        invoice = cursor.fetchone()

        if not invoice:
            return Response(
                json.dumps({"error": "No invoice found for the provided ORDER_NO."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        # Check if the invoice is already canceled
        if invoice.status == "cancel":
            return Response(
                json.dumps({"error": f"Invoice with ORDER_NO {order_no} is already canceled."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Update the invoice status to "cancel"
        cancel_query = """
            UPDATE TaxInv
            SET order_type = 'cancel', update_date = GETDATE()
            WHERE order_no = ?
        """
        cursor.execute(cancel_query, (order_no,))
        conn.commit()


        # Query for response 
        check_query = "SELECT inv_no, order_type, status, update_date FROM TaxInv WHERE order_no = ?"
        cursor.execute(check_query, (order_no,))
        invoice = cursor.fetchone()

        formated_update_date = datetime.strptime(invoice.update_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
        # Map query result to a dictionary
        result = {
            "ORDER_NO": order_no,
            "INV_NO": invoice.inv_no,
            "STATUS": invoice.status,
            "ORDER_TYPE": invoice.order_type,
            "UPDATE_DATE": formated_update_date
        }

        # Return success response
        response_json = json.dumps({
            "code": "200",
            "data": result,
            "message": f"Request for Cancel ORDER_NO {order_no} receipt successfully."
        }, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=200)

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()


@app.route('/searchByTime', methods=['POST'])
@token_required  # Add this line to protect the route
def search_by_time():
    """Search records by creation time within a specified time frame."""
    try:
        # Parse query parameters
        key_code = request.args.get("keyCode")
        sign_date = request.args.get("signDate")
        start_time = request.args.get("startTime")
        end_time = request.args.get("endTime")
        client_signature = request.args.get("signature")

        # Validate required parameters
        if not all([key_code, sign_date, start_time, end_time, client_signature]):
            return Response(
                json.dumps({"error": "Missing required parameters: keyCode, signDate, startTime, endTime, or signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Validate keyCode
        if key_code != "VTI":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        string_to_sign = f"{key_code}{sign_date}{start_time}{end_time}"
        server_signature = generate_signature(key_code, sign_date, string_to_sign)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch records within the time frame
        query = """
            SELECT inv_no, order_no, status, create_date, update_date
            FROM TaxInv
            WHERE create_date BETWEEN ? AND ?
            ORDER BY create_date ASC
        """
        cursor.execute(query, (start_time, end_time))
        records = cursor.fetchall()

        if not records:
            return Response(
                json.dumps({"error": "No records found within the specified time frame."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        
        formated_create_date = datetime.strptime(record.create_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
        formated_update_date = datetime.strptime(record.update_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
       

        # Map query results to a list of dictionaries
        result = [
            {
                "INV_NO": record.inv_no,
                "ORDER_NO": record.order_no,
                "STATUS": record.status,
                "CREATE_DATE": formated_create_date,
                "UPDATE_DATE": formated_update_date
            }
            for record in records
        ]

        # Return the response
        response_json = json.dumps({
            "code": "200",
            "data": result,
            "message": "Records retrieved successfully."
        }, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=200)

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/searchByDate', methods=['POST'])
@token_required  # Add this line to protect the route
def search_by_date():
    """Search records by creation date within a specified date range."""
    try:
        # Parse the JSON payload
        payload = request.get_json()
        if not payload:
            return Response(
                json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract required parameters
        key_code = payload.get("keyCode")
        sign_date = payload.get("signDate") 
        order_no = payload.get("ORDER_NO")
        client_signature = payload.get("signature")

        # Parse query Data parameters
        # Access the nested datum inside Data
        data = payload.get("Data")

        start_date = data.get("startDate") if data else None    # Start date (YYYY-MM-DD)
        end_date =  data.get("endDate") if data else None       # End date (YYYY-MM-DD)
        

        # Validate required parameters
        if not all([key_code, sign_date, start_date, end_date, client_signature]):
            return Response(
                json.dumps({"error": "Missing required parameters: keyCode, signDate, startDate, endDate, or signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Validate keyCode
        if key_code != "VTI":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        # string_to_sign = f"{key_code}{sign_date}{start_date}{end_date}"
        server_signature = generate_signature(key_code, sign_date, order_no)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Ensure dates are formatted correctly
        try:
            start_date = start_date.strip()
            end_date = end_date.strip()
        except Exception as e:
            return Response(
                json.dumps({"error": f"Invalid date format: {str(e)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch records within the date range
        query = """
            SELECT inv_no, order_no, status, order_type, sale_amt_word, fail_reason, create_date, update_date
            FROM TaxInv
            WHERE CAST(create_date AS DATE) BETWEEN ? AND ?
            ORDER BY create_date ASC
        """
        cursor.execute(query, (start_date, end_date))
        records = cursor.fetchall()

        if not records:
            return Response(
                json.dumps({"error": "No records found within the specified date range."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )
        #change format for the date on json output
        # formated_create_date = datetime.strptime(record.create_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
        # formated_update_date = datetime.strptime(record.update_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
    
        # # Map query results to a list of dictionaries
        # result = [
        #     {
        #         "ORDER_NO": record.order_no,
        #         "INV_NO": record.inv_no,
        #         "STATUS": record.status,
        #         "CREATE_DATE": formated_create_date,
        #         "UPDATE_DATE": formated_update_date
        #     }
        #     for record in records
        # ]

        # Map query results to a list of dictionaries
        result = []
        for record in records:
            # Change format for the date on JSON output
            formated_create_date = datetime.strptime(record.create_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
            formated_update_date = datetime.strptime(record.update_date, "%b %d %Y %I:%M%p").strftime("%d/%m/%Y %H:%M:%S")
            
            result.append({
                "ORDER_NO": record.order_no,
                "INV_NO": record.inv_no,
                "STATUS": record.status,
                "ORDER_TYPE": record.order_type,
                "SALE_AMT_WORD": record.sale_amt_word,
                "FAIL_REASON": record.fail_reason,
                "CREATE_DATE": formated_create_date,
                "UPDATE_DATE": formated_update_date
            })




        # Return the response
        response_json = json.dumps({
            "code": "200",
            "data": result,
            "message": "Records retrieved successfully."
        }, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=200)

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/retrieveInvoices', methods=['GET'])
@token_required  # Add this line to protect the route
def retrieve_invoices():
    """Retrieve all invoices with status = 'wait'."""
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
        required_fields = ["keyCode", "signDate", "signature", "Data"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                json.dumps({"error": f"Missing required field(s): {', '.join(missing_fields)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        if data["keyCode"] != "APIS":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract fields
        key_code = data["keyCode"]
        sign_date = data["signDate"]
        client_signature = data["signature"]
        status = data["Data"].get("STATUS")

        # Validate the required "STATUS" field
        if not status or status != "wait":
            return Response(
                json.dumps({"error": "Invalid or missing 'STATUS' in 'Data'. Only 'wait' is allowed."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        #string_to_sign = f"{key_code}{sign_date}{status}"  # I think no need since it is alreaddy in generate_signature function
        server_signature = generate_signature_apis(key_code, sign_date)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch invoices with status = 'wait'
        query = """
            SELECT order_no, status, fail_reason, order_type
            FROM TaxInv
            WHERE status = ?
        """
        cursor.execute(query, (status,))
        invoices = cursor.fetchall()

        if not invoices:
            return Response(
                json.dumps({"error": "No invoices found with status = 'wait'."}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        # Prepare the response for all retrieved invoices
        response_data = [
            {
                "code": "200",
                "data": {
                    "ORDER_NO": invoice.order_no,
                    "STATUS": invoice.status,
                    "FAIL_REASON": invoice.fail_reason or "",
                    "OPER_TYPE": invoice.order_type
                },
                "message": "Invoice retrieved successfully"
            }
            for invoice in invoices
        ]

        # Return the response as JSON
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/retrieveCancelInvoices', methods=['GET'])
@token_required  # Protect the route with the token decorator
def retrieve_cancelinvoices():
    """Retrieve all invoices with status = 'wait' and OPER_TYPE = 'cancel'."""
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
        required_fields = ["keyCode", "signDate", "signature", "Data"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                json.dumps({"error": f"Missing required field(s): {', '.join(missing_fields)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        if data["keyCode"] != "APIS":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract fields
        key_code = data["keyCode"]
        sign_date = data["signDate"]
        client_signature = data["signature"]
        status = data["Data"].get("STATUS")
        oper_type = data["Data"].get("ORDER_TYPE")

        # Validate the required "STATUS" and "OPER_TYPE" fields
        if not status or status != "wait":
            return Response(
                json.dumps({"error": "Invalid or missing 'STATUS' in 'Data'. Only 'wait' is allowed."},
                           ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )
        if not oper_type or oper_type != "cancel":
            return Response(
                json.dumps({"error": "Invalid or missing 'ORDER_TYPE' in 'Data'. Only 'cancel' is allowed."},
                           ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature for validation
        server_signature = generate_signature_apis(key_code, sign_date)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch invoices with status = 'wait' and order_type = 'cancel'
        query = """
            SELECT order_no, status, fail_reason, order_type
            FROM TaxInv
            WHERE status = ? AND order_type = ?
        """
        cursor.execute(query, (status, oper_type))
        invoices = cursor.fetchall()

        if not invoices:
            return Response(
                json.dumps({"error": "No invoices found with status = 'wait' and OPER_TYPE = 'cancel'."},
                           ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        # Prepare the response for all retrieved invoices
        response_data = [
            {
                "code": "200",
                "data": {
                    "ORDER_NO": invoice.order_no,
                    "STATUS": invoice.status,
                    "FAIL_REASON": invoice.fail_reason or "",
                    "OPER_TYPE": invoice.order_type
                },
                "message": "Invoice retrieved successfully"
            }
            for invoice in invoices
        ]

        # Return the response as JSON
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/updateInvoiceStatus', methods=['PATCH'])
@token_required  # Add this line to protect the route
def update_invoice_status():
    """Update the status of an existing invoice in the system."""
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
        required_fields = ["keyCode", "signDate", "ORDER_NO", "signature", "Data"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                json.dumps({"error": f"Missing required field(s): {', '.join(missing_fields)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        if data["keyCode"] != "APIS":
            return Response(
                json.dumps({"error": "Invalid keyCode"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Extract fields
        key_code = data["keyCode"]
        sign_date = data["signDate"]
        order_no = data["ORDER_NO"]
        client_signature = data["signature"]
        update_data = data.get("Data", {})

        # Validate Data fields
        required_data_fields = ["ORDER_NO", "STATUS"]
        missing_data_fields = [field for field in required_data_fields if field not in update_data]
        if missing_data_fields:
            return Response(
                json.dumps({"error": f"Missing required Data field(s): {', '.join(missing_data_fields)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        inv_no = update_data.get("INV_NO")
        status = update_data.get("STATUS")
        fail_reason = update_data.get("FAIL_REASON", "")  # Optional, default to empty string

        allowed_status = ["success", "fail", "cancel"]
        if status not in allowed_status:
            return Response(
                json.dumps({"error": f"Invalid status. Allowed values: {', '.join(allowed_status)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Generate server signature
        # string_to_sign = f"{key_code}{sign_date}{inv_no}"
        server_signature = generate_signature(key_code, order_no, sign_date)

        # Compare client signature with server signature
        if client_signature != server_signature:
            return Response(
                json.dumps({"error": "Invalid signature"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch the existing order_no for validation
        check_query = "SELECT order_no FROM TaxInv WHERE order_no = ?"
        cursor.execute(check_query, (order_no,))
        order_ = cursor.fetchone()

        if not order_:
            return Response(
                json.dumps({"error": f"No Order found with ORDER_NO: {order_no}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )

        # Extract ORDER_NO for response
        # order_no = invoice.order_no

        # Update the invoice status
        update_query = """
            UPDATE TaxInv
            SET inv_no = ?, status = ?, fail_reason = ?, update_date = GETDATE()
            WHERE order_no = ?
        """
        cursor.execute(update_query, (inv_no, status, fail_reason, order_no))
        conn.commit()

        # Prepare the response
        response_data = {
            "code": "200",
            "data": {
                "ORDER_NO": order_no,
                "INV_NO": inv_no,
                "STATUS": status,
                "UPDATE_DATE": cursor.execute("SELECT GETDATE()").fetchone()[0].strftime("%d/%m/%Y %H:%M:%S")
            },
            "message": "Order/Invoice updated successfully"
        }

        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )

    except Exception as e:
        # Handle errors
        response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        return Response(response_json, content_type="application/json; charset=utf-8", status=500)

    finally:
        if 'conn' in locals() and conn:
            conn.close()

from flask import Flask, request, jsonify


# Updated number-to-Lao conversion function
def number_to_lao(number):
    if number == 0:
        return "ສູນ"

    lao_digits = {
        0: "ສູນ", 1: "ໜຶ່ງ", 2: "ສອງ", 3: "ສາມ", 4: "ສີ່",
        5: "ຫ້າ", 6: "ຫົກ", 7: "ເຈັດ", 8: "ແປດ", 9: "ເກົ້າ"
    }

    # Extended units to handle larger numbers
    units = ["", "ສິບ", "ຮ້ອຍ", "ພັນ", "ໝື່ນ", "ແສນ", "ລ້ານ",
             "ສິບລ້ານ", "ຮ້ອຍລ້ານ", "ພັນລ້ານ", "ໝື່ນລ້ານ", "ແສນລ້ານ", "ບິລລິອນ"]

    result = []
    num_str = str(number)
    length = len(num_str)

    for i, digit in enumerate(num_str):
        digit_value = int(digit)
        position = length - i - 1  # Position from the right (0 = ones, 1 = tens, etc.)

        if digit_value == 0:
            continue

        # Special case for "2 in tens place" -> ຊາວ
        if position == 1 and digit_value == 2:
            result.append("ຊາວ")
            continue

        # Handle "ເອັດ" for the last digit "1" (not in the beginning)
        if digit_value == 1 and position == 0 and i > 0:
            result.append("ເອັດ")
            continue

        # Skip "ໜຶ່ງ" for 2-digit numbers starting with 1 (e.g., 10, 11, 12)
        if digit_value == 1 and position == 1 and length == 2:
            result.append("ສິບ")
            continue

        # Skip "ໜຶ່ງ" before "ສິບ" for cases like 111 (ໜຶ່ງຮ້ອຍສິບເອັດ)
        if digit_value == 1 and position == 1:
            result.append(units[position])
            continue

        # Handle special case for numbers like 121, 112, 111, etc.
        if digit_value == 1 and position == 2 and i > 0:
            result.append(lao_digits[digit_value])
            result.append(units[position])
            continue

        # Handle "ໜຶ່ງ" at the start of higher units (e.g., ໜຶ່ງຮ້ອຍ, ໜຶ່ງພັນ)
        if digit_value == 1 and position > 0:
            result.append(lao_digits[digit_value])
            result.append(units[position])
            continue

        # Regular digit translation
        result.append(lao_digits[digit_value])
        result.append(units[position])

    return "".join(result).strip()


# POST API route
@app.route('/convert', methods=['POST'])
@token_required  # Add this line to protect the route
def convert_number():
    try:
        # Get JSON payload from request body
        data = request.get_json()

        if not data or "number" not in data:
            return jsonify({"error": "Missing 'number' in request body"}), 400

        # Extract the number
        number = int(data["number"])
        lao_string = number_to_lao(number)

        return jsonify({"number": number, "lao_string": lao_string})
    except ValueError:
        return jsonify({"error": "Invalid number provided"}), 400


def number_to_words(number):
    units = ["", "ໜຶ່ງ", "ສອງ", "ສາມ", "ສີ່", "ຫ້າ", "ຫົກ", "ເຈັດ", "ແປດ", "ເກົ້າ"]
    teens = ["ສິບ", "ສິບເອັດ", "ສິບສອງ", "ສິບສາມ", "ສິບສີ່", "ສິບຫ້າ", "ສິບຫົກ",
             "ສິບເຈັດ", "ສິບແປດ", "ສິບເກົ້າ"]
    tens = ["", "ສິບ", "ຊາວ", "ສາມສິບ", "ສີ່ສິບ", "ຫ້າສິບ", "ຫົກສິບ", "ເຈັດສິບ",
            "ແປດສິບ", "ເກົ້າສິບ"]

    if number == 0:
        return "ສູນ"
    elif number < 10:
        return units[number]
    elif 10 <= number < 20:
        return teens[number - 10]
    elif 20 <= number < 100:
        if number % 10 == 1:
            return tens[number // 10] + "ເອັດ"
        else:
            return tens[number // 10] + ("" + number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        hundreds_digit = number // 100
        remainder = number % 100
        if remainder == 0:
            return units[hundreds_digit] + "ຮ້ອຍ"
        else:
            return units[hundreds_digit] + "ຮ້ອຍ" + number_to_words(remainder)
    elif 1000 <= number < 100000:
        thousands_part = number // 1000
        remainder = number % 1000
        thousands_word = number_to_words(thousands_part) + "ພັນ"
        if remainder == 0:
            return thousands_word
        else:
            return thousands_word + number_to_words(remainder)
    elif 100000 <= number < 1000000:  # Fix for 100,000 to 999,999
        hundred_thousands_part = number // 100000
        remainder = number % 100000
        hundred_thousands_word = number_to_words(hundred_thousands_part) + "ແສນ"
        if remainder == 0:
            return hundred_thousands_word
        else:
            return hundred_thousands_word + number_to_words(remainder)
    elif 1000000 <= number < 1000000000:
        millions_part = number // 1000000
        remainder = number % 1000000
        millions_word = number_to_words(millions_part) + "ລ້ານ"
        if remainder == 0:
            return millions_word
        else:
            return millions_word + number_to_words(remainder)
    elif 1000000000 <= number < 1000000000000:
        billions_part = number // 1000000000
        remainder = number % 1000000000
        billions_word = number_to_words(billions_part) + "ຕື້"
        if remainder == 0:
            return billions_word
        else:
            return billions_word + number_to_words(remainder)
    else:
        return "Number out of range"

def number_with_decimals_to_words(number):
    """ Convert a number with up to two decimal places to words in Lao. """
    integer_part = int(number)
    decimal_part = round((number - integer_part) * 100)  # Extract two decimal places

    words = number_to_words(integer_part)  # Convert integer part correctly

    if decimal_part > 0:
        decimal_digits = str(decimal_part).zfill(2)  # Ensure two digits
        decimal_words = "ຈຸດ" + "".join([number_to_words(int(digit)) for digit in decimal_digits])
        return words + decimal_words
    else:
        return words

def float_to_words(number_str):
    if '.' in number_str:
        integer_part, decimal_part = number_str.split('.')
        integer_words = number_to_words(int(integer_part))

        decimal_part = decimal_part[:2].ljust(2, '0')  # Ensure two digits
        decimal_words = "ຈຸດ" + "".join([number_to_words(int(digit)) for digit in decimal_part])

        return integer_words + decimal_words
    else:
        return number_to_words(int(number_str))
    
@app.route('/number-to-words', methods=['POST'])
def convert_number_to_words():
    # data = request.get_json()
    # number = data.get('number')

    # if number is None:
    #     return jsonify({"error": "Please provide a number"}), 400

    # try:
    #     number = float(number)
    # except ValueError:
    #     return jsonify({"error": "Invalid number provided"}), 400

    # if number < 0 or number >= 1000000000000:
    #     return jsonify({"error": "Number out of range. Please provide a number between 0 and 999,999,999,999"}), 400

    # words = number_with_decimals_to_words(number)
    # return jsonify({"number": number, "words": words})

    data = request.get_json()
    number_str = data.get('number')

    if number_str is None:
        return jsonify({"code": "400", "message": "Please provide a number"}), 400

    try:
        number_str = str(number_str)  # Keep it as a string to preserve format
        number = float(number_str)  # Convert to float for validation
    except ValueError:
        return jsonify({"code": "400", "message": "Invalid number provided"}), 400

    if number < 0 or number >= 1000000000000:  # Check range
        return jsonify({
            "code": "400",
            "message": "Number out of range. Please provide a number between 0 and 999,999,999,999"
        }), 400

    words = float_to_words(number_str)  # Convert number to words

    return jsonify({
        "code": "200",
        "data": {
            "number": number_str,  # Keep exactly as input
            "words": words
        },
        "message": "success"
    })



if __name__ == "__main__":
    app.run(debug=False)
