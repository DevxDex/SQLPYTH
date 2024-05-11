import mysql.connector
from decimal import Decimal
def create_db_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("MySQL Database connection successful")
    except Exception as err:
        print(f"Error: '{err}'")
    return connection

def execute_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        cursor.execute(query, params if params else ())
        if cursor.with_rows:
            results = cursor.fetchall()
            cursor.close()
            return results
        else:
            connection.commit()
            cursor.close()
    except Exception as err:
        print(f"Error: '{err}'")
        cursor.close()
        return None

def login(connection):
    while True:
        username = input("Enter your username: ")
        query = f"SELECT * FROM USER WHERE name = '{username}'"
        results = execute_query(connection, query)
        if results and len(results) > 0:
            print("Login successful.")
            return results[0]  
        else:
            print("User not found.")
            choice = input("Do you want to register a new account? (yes/no): ")
            if choice.lower() == 'yes':
                register_user(connection, username)
                continue  
            else:
                continue  

def register_user(connection, username):
    if not username.strip():
        print("Username cannot be blank. Please try registering again.")
        return
    phone_num = input("Enter your phone number: ")
    address = input("Enter your address: ")
    while True:
        role = input("Enter your role (Buyer/Seller): ").strip().lower()
        if role in ['buyer', 'seller']:
            break
        print("Invalid role entered. Please enter 'Buyer' or 'Seller'.")
    query = f"""
    INSERT INTO USER (name, phone_num, address, role)
    VALUES ('{username}', '{phone_num}', '{address}', '{role}');
    """
    execute_query(connection, query)
    print(f"User {username} registered successfully.")

def list_items(connection):
    query = """
    SELECT ITEM.id, ITEM.name, ITEM.price, USER.address AS origin
    FROM ITEM
    JOIN USER ON ITEM.seller_id = USER.id
    """
    result = execute_query(connection, query)
    if result:
        print("Items for sale:")
        for item in result:
            item_id, item_name, item_price, item_origin = item
            print(f"ID: {item_id}, Name: {item_name}, Price: ${item_price}, Origin: {item_origin}")
    else:
        print("No items available for sale.")

def admin_menu(connection):
    while True:
        print("\nAdmin Menu:")
        print("1. View Tables")
        print("2. Delete Record by ID and Table Name")
        print("3. Alter Data in a Table")
        print("4. View Table Content")
        print("5. Exit Admin Menu")
        choice = input("Enter your choice: ")

        if choice == "1":
            view_tables(connection)
        elif choice == "2":
            table_name = input("Enter table name: ")
            record_id = input("Enter record ID: ")
            delete_record_by_id(connection, table_name, record_id)
        elif choice == "3":
            alter_data_in_table(connection)
        elif choice == "4":
            table_name = input("Enter the table name to view its content: ")
            view_table_content(connection, table_name)
        elif choice == "5":
            break
            user = None
        else:
            print("Invalid choice. Please try again.")

def view_tables(connection):
    query = "SHOW TABLES"
    tables = execute_query(connection, query)
    print("Available tables in the database:")
    for table in tables:
        print(table[0])

def view_table_content(connection, table_name):
    try:
        query = f"SELECT * FROM {table_name}"
        results = execute_query(connection, query)
        if results:
            print(f"Contents of {table_name}:")
            for row in results:
                print(row)
        else:
            print(f"No data found in {table_name}.")
    except Exception as e:
        print(f"Failed to retrieve data: {str(e)}")

def delete_record_by_id(connection, table_name, record_id):
    try:
        query = f"DELETE FROM {table_name} WHERE id = %s"
        execute_query(connection, query, (record_id,))
        print(f"Record with ID {record_id} deleted from {table_name}.")
    except Exception as e:
        print(f"Failed to delete record: {str(e)}")

def alter_data_in_table(connection):
    table_name = input("Enter the table name: ")
    record_id = input("Enter the record ID to alter: ")
    column_name = input("Enter the column name to alter: ")
    new_value = input("Enter the new value: ")
    try:
        query = f"UPDATE {table_name} SET {column_name} = %s WHERE id = %s"
        execute_query(connection, query, (new_value, record_id))
        print(f"Record updated in {table_name}.")
    except Exception as e:
        print(f"Failed to update record: {str(e)}")

def buy_item(connection, user_id):
    list_items(connection)
    item_id = input("Enter the ID of the item you wish to buy: ")
    if item_id.strip() == '':
        print("Invalid input. Please enter a numeric item ID.")
        return
    try:
        item_id = int(item_id)
    except ValueError:
        print("Invalid input. Item ID must be a number.")
        return

    query = f"SELECT name, price, quantity FROM ITEM WHERE id = {item_id}"
    result = execute_query(connection, query)
    if result and len(result) > 0:
        item_name, price, quantity = result[0]
        current_points = view_reward_points(connection, user_id)
        
        if current_points > 5:
            price = Decimal(price) - Decimal('5.00')
            update_rewards(connection, user_id, -5, is_deduct=True)
            print(f"A $5 discount applied. New price: ${price}")

        if quantity > 0:
            print(f"You have selected: {item_name} - Price: ${price}.")
            print("Proceeding to checkout...")
            payment_method = input("Enter your payment method (Debit Card, Credit Card, PayPal): ").strip().capitalize()
            if payment_method not in ['Credit card', 'Paypal', 'Debit card']:
                print("Unsupported payment method. Transaction cancelled.")
                return
            confirm = input(f"Confirm purchase of {item_name} for ${price} using {payment_method}? (yes/no): ").strip().lower()
            if confirm == 'yes':
                process_payment(connection, user_id, item_id, price, payment_method)
                create_shipment(connection, item_id, 'Warehouse', 'Customer Address')
                points_awarded = int(price // 10)
                update_rewards(connection, user_id, points_awarded)
                new_quantity = quantity - 1
                if new_quantity > 0:
                    update_query = f"UPDATE ITEM SET quantity = {new_quantity} WHERE id = {item_id}"
                    execute_query(connection, update_query)
                    print("Purchase successful. Item quantity updated.")
                else:
                    delete_related_payments(connection, item_id)
                    delete_query = f"DELETE FROM ITEM WHERE id = {item_id}"
                    execute_query(connection, delete_query)
                    print("Purchase successful. Item sold out and removed from listing.")
            else:
                print("Purchase cancelled.")
        else:
            print("This item is currently out of stock.")
    else:
        print("Item not found.")



def delete_related_payments(connection, item_id):
    delete_payments_query = f"DELETE FROM PAYMENT WHERE item_id = {item_id}"
    execute_query(connection, delete_payments_query)

def process_payment(connection, user_id, item_id, amount, payment_method):
    query = f"""
    INSERT INTO PAYMENT (user_id, item_id, amount, payment_date, payment_method, status)
    VALUES ({user_id}, {item_id}, {amount}, CURDATE(), '{payment_method}', 'Completed');
    """
    execute_query(connection, query)
    print("Payment processed successfully.")

def create_shipment(connection, item_id, origin, destination):
    query = f"""
    INSERT INTO SHIPMENT (item_id, origin, destination)
    VALUES ({item_id}, '{origin}', '{destination}');
    """
    execute_query(connection, query)
    print("Shipment created successfully.")

def view_reward_points(connection, user_id):
    query = f"SELECT points FROM AWARD_POINTS WHERE user_id = {user_id}"
    result = execute_query(connection, query)
    if result and result[0][0] is not None:
        points = result[0][0]
    else:
        points = 0  
    print(f"You currently have {points} reward points.")
    return points


def update_rewards(connection, user_id, points, is_deduct=False):
    current_points = view_reward_points(connection, user_id)
    if current_points is not None:
        if is_deduct:
            new_points = current_points + points
        else:
            new_points = current_points + points
        update_query = "UPDATE AWARD_POINTS SET points = %s WHERE user_id = %s"
        execute_query(connection, update_query, (new_points, user_id))
    else:
        insert_query = "INSERT INTO AWARD_POINTS (user_id, points) VALUES (%s, %s)"
        execute_query(connection, insert_query, (user_id, points))
    print(f"Reward points updated to {new_points if current_points is not None else points}.")


def update_user_role(connection, user_id):
    new_role = input("Enter new role (Buyer/Seller): ").strip().capitalize()
    if new_role not in ['Buyer', 'Seller']:
        print("Invalid role. Please enter 'Buyer' or 'Seller'.")
        return
    query = f"UPDATE USER SET role = '{new_role}' WHERE id = {user_id}"
    execute_query(connection, query)
    print(f"Role updated successfully to {new_role}.")

def change_shipping_info(connection, user_id):
    new_address = input("Enter your new shipping address: ")
    if not new_address:
        print("Shipping address cannot be empty.")
        return
    query = f"UPDATE USER SET address = '{new_address}' WHERE id = {user_id}"
    execute_query(connection, query)
    print("Shipping information updated successfully.")

def update_role_to_seller(connection, user_id):
    update_query = f"UPDATE USER SET role = 'Seller' WHERE id = {user_id}"
    execute_query(connection, update_query)
    print("Your account has been updated to a Seller account. You can now list items for sale.")

def sell_item(connection, user_id):
    role_check_query = f"SELECT role FROM USER WHERE id = {user_id}"
    result = execute_query(connection, role_check_query)
    if result and result[0][0].lower == 'seller':
        item_name = input("Enter the name of the item: ")
        if not item_name.strip():
            print("Item name cannot be blank.")
            return
        item_price = input("Enter the price of the item: ")
        try:
            item_price = float(item_price)
        except ValueError:
            print("Invalid price. Please enter a numeric value.")
            return
        item_quantity = input("Enter the quantity: ")
        try:
            item_quantity = int(item_quantity)
        except ValueError:
            print("Invalid quantity. Please enter a whole number.")
            return
        query = f"""
        INSERT INTO ITEM (name, price, quantity, seller_id)
        VALUES ('{item_name}', {item_price}, {item_quantity}, {user_id})
        """
        execute_query(connection, query)
        print("Item listed for sale")
    else:
        print("Only sellers can list items. Your account does not have selling privileges.")
        choice = input("Would you like to register as a seller? (yes/no): ").strip().lower()
        if choice == 'yes':
            update_role_to_seller(connection, user_id)
        else:
            print("Action cancelled.")

def settings_menu(connection, user_id):
    print("Settings Menu:")
    print("1. Update Role")
    print("2. Change Shipping Information")
    choice = input("Enter your choice: ")
    if choice == "1":
        update_user_role(connection, user_id)
    elif choice == "2":
        change_shipping_info(connection, user_id)
    else:
        print("Invalid choice. Returning to main menu.")

def main():
    connection = create_db_connection("localhost", "root", "", "MarketplaceDB")
    user = None
    while True:
        if user:
            if user[1] == "admin":
                password = input("Enter admin password: ")
                if password == "1337":
                    admin_menu(connection)
                else:
                    print("Incorrect password. Access denied.")
                    quit()
            print("1. Buy item")
            print("2. Sell item")
            print("3. View Reward Points")
            print("4. Settings")
            print("5. Logout")
            choice = input("Enter your choice: ")
            if choice == "1":
                buy_item(connection, user[0])
            elif choice == "2":
                sell_item(connection, user[0])
            elif choice == "3":
                view_reward_points(connection, user[0])
            elif choice == "4":
                settings_menu(connection, user[0])
            elif choice == "5":
                user = None
                print("Logged out.")
            else:
                print("Invalid choice.")
        else:
            print("1. Login")
            print("2. Exit")
            choice = input("Enter your choice: ")
            if choice == "1":
                user = login(connection)
            elif choice == "2":
                print("Exiting...")
                break
            else:
                print("Invalid choice.")

if __name__ == "__main__":
    main()
