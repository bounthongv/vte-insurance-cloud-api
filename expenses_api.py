from flask import Blueprint, request, Response, jsonify
import json
import pyodbc
from decimal import Decimal, InvalidOperation # <--- AND THIS LINE
# Import the shared functions we just created
from shared_utils import get_db_connection, token_required, generate_signature, clean_string

# 2. Create your new expense endpoints using the blueprint decorator
# 1. Create a Blueprint object for all expense-related endpoints.
# All routes in this file will start with /expense
expenses_bp = Blueprint('expenses_api', __name__, url_prefix='/expense')

@expenses_bp.route('/upload', methods=['POST'])
@token_required
def upload_expense():
    """
    Receives an expense JSON payload, validates it, and inserts it into the 
    'expense', 'tbl_dr', and 'tbl_cr' tables.
    """
    conn = None  # Initialize connection to None for the finally block
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract root-level fields
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        exp_no = clean_string(data.get("exp_no"))
        client_signature = data.get("sign")
        exp_data = data.get("exp")
        exp_desc = exp_data.get("exp_desc") if exp_data else None

        # Validate presence of required fields
        if not all([key_code, sign_date, exp_no, client_signature, exp_data, exp_desc]):
            return jsonify({"error": "Missing required fields: keyCode, signDate, exp_no, sign, exp object, or exp_desc"}), 400

        if key_code != "VTI":
            return jsonify({"error": "Invalid keyCode"}), 400

        # --- 2. Authenticate the Signature ---
        # The signature uses keyCode, signDate, and exp_no
        server_signature = generate_signature(key_code, sign_date, exp_no)
        if client_signature != server_signature:
            return jsonify({"error": "Invalid signature"}), 400
            
        # --- 3. Validate Debit and Credit Entries ---
        debit_entries = exp_data.get("debit")
        credit_entries = exp_data.get("credit")

        if not debit_entries or not isinstance(debit_entries, list) or len(debit_entries) == 0:
            return jsonify({"error": "Missing, invalid, or empty 'debit' array"}), 400
        if not credit_entries or not isinstance(credit_entries, list) or len(credit_entries) == 0:
            return jsonify({"error": "Missing, invalid, or empty 'credit' array"}), 400

        # --- 4. Core Business Logic: Sum and Compare Debit/Credit Amounts ---
        total_debit = Decimal('0')
        total_credit = Decimal('0')

        try:
            # Calculate total debit, handling potential formatting issues (e.g., commas)
            for item in debit_entries:
                amount_str = str(item.get('dr_amt', '0')).replace(',', '')
                total_debit += Decimal(amount_str)

            # Calculate total credit
            for item in credit_entries:
                amount_str = str(item.get('cr_amt', '0')).replace(',', '')
                total_credit += Decimal(amount_str)

        except (InvalidOperation, TypeError, KeyError) as e:
            return jsonify({"error": f"Invalid amount format in debit/credit entries. Please check all dr_amt and cr_amt values. Details: {e}"}), 400

        # The fundamental rule of accounting: debits must equal credits
        if total_debit != total_credit:
            return jsonify({
                "error": "Debit and Credit totals do not match.",
                "data": {
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit)
                }
            }), 400

        # --- 5. Database Operations ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into the main 'expense' table
        # Status is hardcoded to 'wait' for security and workflow consistency.
        # create_date and update_date are handled by the database for accuracy.
        expense_query = """
            INSERT INTO expense (exp_no, status, exp_desc, create_date, update_date)
            VALUES (?, 'wait', ?, GETDATE(), GETDATE())
        """
        cursor.execute(expense_query, exp_no, exp_desc)

        # Insert into 'tbl_dr'
        dr_query = "INSERT INTO tbl_dr (exp_no, exp_id, dr_ac, dr_amt) VALUES (?, ?, ?, ?)"
        for item in debit_entries:
            # Validate that each debit item has the required keys
            if not all(k in item for k in ['dr_ac', 'dr_amt']):
                conn.rollback() # Important: undo the main insert if child data is bad
                return jsonify({"error": "A debit entry is missing a required field (dr_ac, or dr_amt)"}), 400
            
        
            exp_id = clean_string(item.get('exp_id'))
            dr_ac = clean_string(item.get('dr_ac'))
            dr_amt = Decimal(str(item.get('dr_amt', '0')).replace(',', ''))
            
            dr_params = (exp_no, exp_id, dr_ac, dr_amt)
            cursor.execute(dr_query, dr_params)
        
        # Insert into 'tbl_cr'
        cr_query = "INSERT INTO tbl_cr (exp_no, exp_id, cr_ac, cr_amt) VALUES (?, ?, ?, ?)"
        for item in credit_entries:
            # Validate that each credit item has the required keys
            if not all(k in item for k in ['cr_ac', 'cr_amt']):
                conn.rollback() # Important: undo all previous inserts
                return jsonify({"error": "A credit entry is missing a required field (cr_ac, or cr_amt)"}), 400

            exp_id = clean_string(item.get('exp_id'))
            cr_ac = clean_string(item.get('cr_ac'))
            cr_amt = Decimal(str(item.get('cr_amt', '0')).replace(',', ''))

            cr_params = (exp_no, exp_id, cr_ac, cr_amt)
            cursor.execute(cr_query, cr_params)

        # If all inserts were successful, commit the transaction
        conn.commit()

        # --- 6. Return Success Response ---
        return jsonify({
            "code": "200",
            "data": {
                "exp_no": exp_no
            },
            "message": "Expense uploaded successfully"
        }), 201 # 201 Created is the most appropriate status code here

    except pyodbc.IntegrityError as e:
        # This specifically handles the case where exp_no already exists (Primary Key violation)
        if "primary key constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            return jsonify({"error": f"Duplicate entry: An expense with exp_no '{exp_no}' already exists."}), 409 # 409 Conflict is good for duplicates
        else:
            return jsonify({"error": f"Database integrity error: {str(e)}"}), 500

    except Exception as e:
        # Generic catch-all for any other unexpected errors
        # In a real production system, you would log this error.
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        # Ensure the database connection is always closed, even if errors occur
        if conn:
            conn.close()


@expenses_bp.route('/getStatus', methods=['POST'])
@token_required
def get_expense_status():
    """
    Checks the processing status of a previously uploaded expense by its exp_no.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract root-level fields
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        exp_no = data.get("exp_no")
        client_signature = data.get("sign")

        # Validate presence of required fields
        if not all([key_code, sign_date, exp_no, client_signature]):
            return jsonify({"error": "Missing required fields: keyCode, signDate, exp_no, or sign"}), 400

        if key_code != "VTI":
            return jsonify({"error": "Invalid keyCode"}), 400

        # --- 2. Authenticate the Signature ---
        # The signature uses keyCode, signDate, and exp_no
        server_signature = generate_signature(key_code, sign_date, exp_no)
        if client_signature != server_signature:
            return jsonify({"error": "Invalid signature"}), 400

        # --- 3. Database Query ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch the expense status from the main 'expense' table
        query = """
            SELECT exp_no, status, fail_reason, create_date, update_date
            FROM expense
            WHERE exp_no = ?
        """
        cursor.execute(query, exp_no)
        expense_record = cursor.fetchone()

        # --- 4. Handle "Not Found" Case ---
        if not expense_record:
            return jsonify({
                "error": f"No expense found with exp_no '{exp_no}'."
            }), 404

        # --- 5. Format and Return Success Response ---
        # The dates from the DB are likely strings, let's just pass them through.
        # If they were datetime objects, we'd format them:
        # update_date = expense_record.update_date.strftime("%d/%m/%Y %H:%M:%S") if expense_record.update_date else None
        
        result = {
            "exp_no": expense_record.exp_no,
            "status": expense_record.status,
            "fail_reason": expense_record.fail_reason or "", # Return empty string if NULL
            "create_date": expense_record.create_date,
            "update_date": expense_record.update_date
        }

        return jsonify({
            "code": "200",
            "data": result,
            "message": "Expense status retrieved successfully"
        }), 200

    except Exception as e:
        # Generic catch-all for any unexpected errors
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        # Ensure the database connection is always closed
        if conn:
            conn.close()


# ... (existing imports, upload_expense, and get_expense_status are above this) ...

@expenses_bp.route('/cancel', methods=['PATCH'])
@token_required
def cancel_expense():
    """
    Requests to cancel an existing expense by updating its status to 'cancel'.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract root-level fields
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        exp_no = data.get("exp_no")
        client_signature = data.get("sign")

        # Validate presence of required fields
        if not all([key_code, sign_date, exp_no, client_signature]):
            return jsonify({"error": "Missing required fields: keyCode, signDate, exp_no, or sign"}), 400

        if key_code != "VTI":
            return jsonify({"error": "Invalid keyCode"}), 400

        # --- 2. Authenticate the Signature ---
        server_signature = generate_signature(key_code, sign_date, exp_no)
        if client_signature != server_signature:
            return jsonify({"error": "Invalid signature"}), 400

        # --- 3. Database Operations ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # First, check if the expense exists and what its current status is
        check_query = "SELECT status FROM expense WHERE exp_no = ?"
        cursor.execute(check_query, exp_no)
        expense_record = cursor.fetchone()

        # Handle "Not Found" case
        if not expense_record:
            return jsonify({"error": f"No expense found with exp_no '{exp_no}'."}), 404

        # Prevent re-cancelling an already cancelled expense
        if expense_record.status == 'cancel':
            return jsonify({"error": f"Expense with exp_no '{exp_no}' is already canceled."}), 400 # 400 Bad Request is appropriate here

        # Prevent cancelling an expense that has already been processed successfully
        if expense_record.status == 'success':
             return jsonify({"error": f"Cannot cancel expense with exp_no '{exp_no}' because it has already succeeded."}), 400

        # Update the expense status to 'cancel' and set the update_date
        cancel_query = """
            UPDATE expense
            SET status = 'cancel', update_date = GETDATE()
            WHERE exp_no = ?
        """
        cursor.execute(cancel_query, exp_no)
        conn.commit()

        # --- 4. Fetch the updated record for the response ---
        # (This confirms the update was successful)
        cursor.execute(check_query, exp_no) # Re-run the check query
        updated_expense = cursor.fetchone()

        # --- 5. Format and Return Success Response ---
        result = {
            "exp_no": exp_no,
            "status": updated_expense.status
        }

        return jsonify({
            "code": "200",
            "data": result,
            "message": f"Request to cancel expense '{exp_no}' was successful."
        }), 200

    except Exception as e:
        # Generic catch-all for any unexpected errors
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        # Ensure the database connection is always closed
        if conn:
            conn.close()


# ... (existing imports and other functions are above this) ...
# You can remove 'import hashlib' if it's no longer used elsewhere in this file.

@expenses_bp.route('/searchByDate', methods=['POST'])
@token_required
def search_expense_by_date():
    """
    Searches for expense records created within a specified date range.
    Uses a 'request_no' for signature consistency with other endpoints.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract root-level fields for authentication
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        request_no = data.get("request_no") # Use the new field for the signature
        client_signature = data.get("sign")
        
        # Extract the date range from the 'Data' object
        search_data = data.get("Data")
        if not search_data:
             return jsonify({"error": "Missing 'Data' object in the payload"}), 400

        start_date_str = search_data.get("startDate") # Expected format: 'YYYY-MM-DD'
        end_date_str = search_data.get("endDate")   # Expected format: 'YYYY-MM-DD'

        # Validate presence of all required fields
        if not all([key_code, sign_date, request_no, client_signature, start_date_str, end_date_str]):
            return jsonify({"error": "Missing required fields: keyCode, signDate, request_no, sign, startDate, or endDate"}), 400

        if key_code != "VTI":
            return jsonify({"error": "Invalid keyCode"}), 400
            
        # --- 2. Authenticate the Signature (Client-Consistent Method) ---
        # The signature now uses the familiar pattern: keyCode, signDate, and request_no
        server_signature = generate_signature(key_code, sign_date, request_no)
        if client_signature != server_signature:
            return jsonify({"error": "Invalid signature"}), 400

        # --- 3. Database Query ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch records within the date range.
        # We CAST create_date to DATE to ignore the time part for the comparison.
        query = """
            SELECT exp_no, status, fail_reason, create_date, update_date
            FROM expense
            WHERE CAST(create_date AS DATE) BETWEEN ? AND ?
            ORDER BY create_date ASC
        """
        cursor.execute(query, (start_date_str, end_date_str))
        records = cursor.fetchall()

        # --- 4. Handle "No Records Found" Case ---
        if not records:
            return jsonify({
                "code": "200",
                "data": [], # Return an empty list
                "message": "No expense records found within the specified date range."
            }), 200

        # --- 5. Format and Return Success Response ---
        result_list = []
        for record in records:
            result_list.append({
                "exp_no": record.exp_no,
                "status": record.status,
                "fail_reason": record.fail_reason or "",
                "create_date": record.create_date,
                "update_date": record.update_date
            })

        return jsonify({
            "code": "200",
            "data": result_list,
            "message": "Expense records retrieved successfully."
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()

# ... (existing imports and other functions are above this) ...

@expenses_bp.route('/retrieve', methods=['GET'])
@token_required
def retrieve_expenses():
    """
    Retrieves all expense records that match a given status.
    The status is provided in the JSON request body.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract root-level fields for authentication
        key_code = data.get("keyCode")
        sign_date = data.get("signDate")
        client_signature = data.get("sign")
        
        # Extract the status from the 'Data' object
        search_data = data.get("Data")
        if not search_data:
             return jsonify({"error": "Missing 'Data' object in the payload"}), 400

        status_to_retrieve = search_data.get("status")

        # Validate the provided status
        allowed_statuses = ['wait', 'cancel', 'pending', 'success', 'fail']
        if not status_to_retrieve or status_to_retrieve not in allowed_statuses:
            return jsonify({
                "error": "Missing or invalid 'status' in 'Data' object.",
                "allowed_values": allowed_statuses
            }), 400

        # --- 2. Authenticate the Signature ---
        # For a general retrieval action, the signature can be based on keyCode and signDate.
        # We need a consistent way to handle signatures for non-ID specific actions.
        # Let's use the pattern from searchByDate, expecting a 'request_no'.
        request_no = data.get("request_no")
        if not all([key_code, sign_date, request_no, client_signature]):
            return jsonify({"error": "Missing required fields for authentication: keyCode, signDate, request_no, or sign"}), 400

        if key_code != "VTI": # Assuming VTI is the system calling this
            return jsonify({"error": "Invalid keyCode for this operation"}), 400

        server_signature = generate_signature(key_code, sign_date, request_no)
        if client_signature != server_signature:
            return jsonify({"error": "Invalid signature"}), 400

        # --- 3. Database Query ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch records matching the specified status
        query = """
            SELECT exp_no, status, fail_reason, create_date, update_date
            FROM expense
            WHERE status = ?
            ORDER BY create_date ASC
        """
        cursor.execute(query, status_to_retrieve)
        records = cursor.fetchall()

        # --- 4. Handle "No Records Found" Case ---
        if not records:
            return jsonify({
                "code": "200",
                "data": [], # Return an empty list
                "message": f"No expense records found with status '{status_to_retrieve}'."
            }), 200

        # --- 5. Format and Return Success Response ---
        result_list = []
        for record in records:
            result_list.append({
                "exp_no": record.exp_no,
                "status": record.status,
                "fail_reason": record.fail_reason or "", # Ensure this is always present
                "create_date": record.create_date,
                "update_date": record.update_date
            })

        return jsonify({
            "code": "200",
            "data": result_list,
            "message": f"Expense records with status '{status_to_retrieve}' retrieved successfully."
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()