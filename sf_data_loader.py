"""
Salesforce Data Loader — Vendor Contacts & Contracts
=====================================================
Loads sf_contacts.csv and sf_contracts.csv into Salesforce
custom objects via REST API using Username-Password OAuth flow.

Usage:
    1. Fill in your credentials in the CONFIG section below
    2. Run: python sf_data_loader.py
    
Requirements:
    pip install requests
"""

import requests
import csv
import json
import sys
import time
from pathlib import Path


# ============================================================
# CONFIG — Fill in your Salesforce credentials here
# ============================================================

SF_USERNAME = "your_salesforce_username@example.com"
SF_PASSWORD = "your_password"
SF_SECURITY_TOKEN = "your_security_token"

# For Developer Edition / Production, use:
SF_LOGIN_URL = "https://login.salesforce.com"

# For Sandbox, use instead:
# SF_LOGIN_URL = "https://test.salesforce.com"

SF_API_VERSION = "v59.0"

# File paths (update if your files are in a different location)
CONTACTS_CSV = "sf_contacts.csv"
CONTRACTS_CSV = "sf_contracts.csv"

# ============================================================
# END CONFIG
# ============================================================


class SalesforceLoader:
    """Handles authentication and data loading to Salesforce."""

    def __init__(self):
        self.access_token = None
        self.instance_url = None

    # --------------------------------------------------------
    # STEP 1: Login to Salesforce
    # --------------------------------------------------------
    def login(self):
        """
        Authenticate using Username-Password OAuth flow.
        
        How it works:
        - Sends your username + password + security token to Salesforce
        - Salesforce returns an access_token and instance_url
        - All subsequent API calls use this token
        """
        print("\n" + "=" * 60)
        print("STEP 1: Logging into Salesforce...")
        print("=" * 60)

        url = f"{SF_LOGIN_URL}/services/oauth2/token"

        payload = {
            "grant_type": "password",
            "client_id": "3MVG9d8..z.hDcPJVpNMO6GR3GjJE_PLACEHOLDER",  # See note below
            "client_secret": "PLACEHOLDER",  # See note below
            "username": SF_USERNAME,
            "password": SF_PASSWORD + SF_SECURITY_TOKEN,
        }

        # ---------------------------------------------------------
        # NOTE: For Username-Password flow without a Connected App,
        # you can use the Salesforce CLI's default connected app.
        # Replace client_id and client_secret with your own, OR
        # use the simple_salesforce library (see Alternative below).
        # ---------------------------------------------------------

        # === RECOMMENDED: Use simple_salesforce instead ===
        # This is much simpler and doesn't need client_id/secret
        try:
            from simple_salesforce import Salesforce

            print(f"  Connecting as: {SF_USERNAME}")
            print(f"  Login URL:    {SF_LOGIN_URL}")

            sf = Salesforce(
                username=SF_USERNAME,
                password=SF_PASSWORD,
                security_token=SF_SECURITY_TOKEN,
                domain="login",  # Use "test" for sandbox
            )

            self.access_token = sf.session_id
            self.instance_url = sf.sf_instance
            self.sf = sf

            print(f"\n  ✅ Login successful!")
            print(f"  Instance URL: https://{self.instance_url}")
            print(f"  Session ID:   {self.access_token[:30]}...")
            return True

        except ImportError:
            print("\n  ❌ simple_salesforce not installed.")
            print("  Run: pip install simple_salesforce")
            print("\n  Falling back to raw REST API...")
            return self._login_rest(url, payload)

        except Exception as e:
            print(f"\n  ❌ Login failed: {e}")
            print("\n  Common fixes:")
            print("  1. Check username, password, and security token")
            print("  2. If you reset your password, Salesforce emails a new security token")
            print("  3. To get a new token: Setup → My Personal Information → Reset My Security Token")
            return False

    def _login_rest(self, url, payload):
        """Fallback: Raw REST API login."""
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.instance_url = data["instance_url"]
                print(f"  ✅ Login successful!")
                print(f"  Instance URL: {self.instance_url}")
                return True
            else:
                print(f"  ❌ Login failed: {response.status_code}")
                print(f"  Error: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            return False

    # --------------------------------------------------------
    # STEP 2: Verify Vendor Accounts exist
    # --------------------------------------------------------
    def verify_accounts(self):
        """
        Before loading contacts/contracts, verify that
        Vendor Account records exist in Salesforce.
        """
        print("\n" + "=" * 60)
        print("STEP 2: Verifying Vendor Accounts exist...")
        print("=" * 60)

        query = "SELECT Vendor_ID__c, Name FROM Vendor_Account__c ORDER BY Vendor_ID__c"

        try:
            results = self.sf.query(query)
            records = results["records"]

            if len(records) == 0:
                print("\n  ❌ No Vendor Account records found!")
                print("  You must import Vendor Accounts first before loading Contacts/Contracts.")
                return False, {}

            # Build a lookup map: Vendor_ID → Salesforce Record ID
            vendor_map = {}
            print(f"\n  Found {len(records)} Vendor Accounts:\n")
            for rec in records:
                vendor_id = rec["Vendor_ID__c"]
                sf_id = rec["Id"]
                name = rec["Name"]
                vendor_map[vendor_id] = sf_id
                print(f"    {vendor_id} → {name} (ID: {sf_id})")

            print(f"\n  ✅ All {len(records)} Vendor Accounts verified!")
            return True, vendor_map

        except Exception as e:
            print(f"\n  ❌ Query failed: {e}")
            print("  Make sure the Vendor_Account__c object exists and has records.")
            return False, {}

    # --------------------------------------------------------
    # STEP 3: Load Vendor Contacts
    # --------------------------------------------------------
    def load_contacts(self, vendor_map):
        """
        Read sf_contacts.csv and create Vendor_Contact__c records.
        Links each contact to its parent Vendor Account using the vendor_map.
        """
        print("\n" + "=" * 60)
        print("STEP 3: Loading Vendor Contacts...")
        print("=" * 60)

        if not Path(CONTACTS_CSV).exists():
            print(f"\n  ❌ File not found: {CONTACTS_CSV}")
            print(f"  Make sure the file is in the same directory as this script.")
            return False

        # Read CSV
        with open(CONTACTS_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            contacts = list(reader)

        print(f"\n  Found {len(contacts)} contacts in CSV")

        success_count = 0
        error_count = 0
        errors = []

        for i, row in enumerate(contacts, 1):
            # Clean whitespace from keys and values
            row = {k.strip(): v.strip() for k, v in row.items()}

            vendor_id = row.get("Account.Vendor_ID__c", "")
            first_name = row.get("FirstName", "")
            last_name = row.get("LastName", "")

            # Look up the Salesforce ID for the parent Vendor Account
            sf_account_id = vendor_map.get(vendor_id)

            if not sf_account_id:
                error_msg = f"  ❌ Row {i}: Vendor ID '{vendor_id}' not found in Salesforce"
                print(error_msg)
                errors.append(error_msg)
                error_count += 1
                continue

            # Build the record payload
            contact_data = {
                "Name": f"{first_name} {last_name}",
                "Contact_ID__c": row.get("Contact_ID__c", ""),
                "Vendor_Account__c": sf_account_id,  # Lookup by SF ID
                "Vendor_ID_Reference__c": vendor_id,
                "First_Name__c": first_name,
                "Last_Name__c": last_name,
                "Email__c": row.get("Email", ""),
                "Phone__c": row.get("Phone", ""),
                "Title__c": row.get("Title", ""),
                "Contact_Type__c": row.get("Contact_Type__c", ""),
                "Is_Active__c": row.get("Is_Active__c", "true").lower() == "true",
            }

            try:
                result = self.sf.Vendor_Contact__c.create(contact_data)

                if result["success"]:
                    print(f"  ✅ [{i:02d}/50] {first_name} {last_name} ({vendor_id}) → Created: {result['id']}")
                    success_count += 1
                else:
                    error_msg = f"  ❌ [{i:02d}/50] {first_name} {last_name}: {result['errors']}"
                    print(error_msg)
                    errors.append(error_msg)
                    error_count += 1

            except Exception as e:
                error_msg = f"  ❌ [{i:02d}/50] {first_name} {last_name}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                error_count += 1

            # Small delay to avoid API rate limits
            if i % 10 == 0:
                time.sleep(0.5)

        print(f"\n  {'=' * 40}")
        print(f"  CONTACTS SUMMARY")
        print(f"  {'=' * 40}")
        print(f"  ✅ Succeeded: {success_count}")
        print(f"  ❌ Failed:    {error_count}")
        print(f"  Total:       {success_count + error_count}")

        if errors:
            print(f"\n  Errors:")
            for err in errors:
                print(f"    {err}")

        return error_count == 0

    # --------------------------------------------------------
    # STEP 4: Load Vendor Contracts
    # --------------------------------------------------------
    def load_contracts(self, vendor_map):
        """
        Read sf_contracts.csv and create Vendor_Contract__c records.
        Links each contract to its parent Vendor Account using the vendor_map.
        """
        print("\n" + "=" * 60)
        print("STEP 4: Loading Vendor Contracts...")
        print("=" * 60)

        if not Path(CONTRACTS_CSV).exists():
            print(f"\n  ❌ File not found: {CONTRACTS_CSV}")
            print(f"  Make sure the file is in the same directory as this script.")
            return False

        # Read CSV
        with open(CONTRACTS_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            contracts = list(reader)

        print(f"\n  Found {len(contracts)} contracts in CSV")

        success_count = 0
        error_count = 0
        errors = []

        for i, row in enumerate(contracts, 1):
            # Clean whitespace
            row = {k.strip(): v.strip() for k, v in row.items()}

            vendor_id = row.get("Account.Vendor_ID__c", "")
            contract_id = row.get("Contract_ID__c", "")

            # Look up parent Account
            sf_account_id = vendor_map.get(vendor_id)

            if not sf_account_id:
                error_msg = f"  ❌ Row {i}: Vendor ID '{vendor_id}' not found in Salesforce"
                print(error_msg)
                errors.append(error_msg)
                error_count += 1
                continue

            # Build the record payload
            contract_data = {
                "Name": contract_id,  # Record Name field
                "Contract_External_ID__c": contract_id,
                "Vendor_Account__c": sf_account_id,
                "Start_Date__c": row.get("StartDate", ""),
                "End_Date__c": row.get("EndDate", ""),
                "Status__c": row.get("Status", ""),
                "Payment_Terms__c": row.get("Payment_Terms__c", ""),
                "Contract_Value__c": float(row.get("Contract_Value__c", 0)),
                "SLA_Response_Hours__c": int(row.get("SLA_Response_Hours__c", 0)),
                "SLA_Resolution_Days__c": int(row.get("SLA_Resolution_Days__c", 0)),
                "Late_Penalty__c": row.get("Late_Penalty__c", ""),
                "Review_Frequency__c": row.get("Review_Frequency__c", ""),
                "Description__c": row.get("Description", ""),
            }

            try:
                result = self.sf.Vendor_Contract__c.create(contract_data)

                if result["success"]:
                    print(f"  ✅ [{i:02d}/25] {contract_id} ({vendor_id}) → Created: {result['id']}")
                    success_count += 1
                else:
                    error_msg = f"  ❌ [{i:02d}/25] {contract_id}: {result['errors']}"
                    print(error_msg)
                    errors.append(error_msg)
                    error_count += 1

            except Exception as e:
                error_msg = f"  ❌ [{i:02d}/25] {contract_id}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                error_count += 1

            # Small delay to avoid API rate limits
            if i % 10 == 0:
                time.sleep(0.5)

        print(f"\n  {'=' * 40}")
        print(f"  CONTRACTS SUMMARY")
        print(f"  {'=' * 40}")
        print(f"  ✅ Succeeded: {success_count}")
        print(f"  ❌ Failed:    {error_count}")
        print(f"  Total:       {success_count + error_count}")

        if errors:
            print(f"\n  Errors:")
            for err in errors:
                print(f"    {err}")

        return error_count == 0

    # --------------------------------------------------------
    # STEP 5: Verify everything was loaded
    # --------------------------------------------------------
    def verify_data(self):
        """Run verification queries to confirm data was loaded correctly."""
        print("\n" + "=" * 60)
        print("STEP 5: Verifying loaded data...")
        print("=" * 60)

        # Count contacts
        try:
            result = self.sf.query("SELECT COUNT() FROM Vendor_Contact__c")
            contact_count = result["totalSize"]
            print(f"\n  Vendor Contacts in Salesforce: {contact_count}")
        except Exception as e:
            print(f"\n  ❌ Could not count contacts: {e}")
            contact_count = 0

        # Count contracts
        try:
            result = self.sf.query("SELECT COUNT() FROM Vendor_Contract__c")
            contract_count = result["totalSize"]
            print(f"  Vendor Contracts in Salesforce: {contract_count}")
        except Exception as e:
            print(f"\n  ❌ Could not count contracts: {e}")
            contract_count = 0

        # Show a sample: Vendor Account with its contacts and contracts
        print(f"\n  --- Sample: Acme Industrial Supplies (V-001) ---")

        try:
            contacts = self.sf.query(
                "SELECT Name, Email__c, Contact_Type__c "
                "FROM Vendor_Contact__c "
                "WHERE Vendor_ID_Reference__c = 'V-001'"
            )
            print(f"\n  Contacts:")
            for rec in contacts["records"]:
                print(f"    • {rec['Name']} ({rec['Email__c']}) — {rec['Contact_Type__c']}")
        except Exception as e:
            print(f"  ❌ Could not query contacts: {e}")

        try:
            contracts = self.sf.query(
                "SELECT Name, Status__c, Contract_Value__c "
                "FROM Vendor_Contract__c "
                "WHERE Vendor_Account__r.Vendor_ID__c = 'V-001'"
            )
            print(f"\n  Contracts:")
            for rec in contracts["records"]:
                print(f"    • {rec['Name']} — {rec['Status__c']} — ₹{rec['Contract_Value__c']:,.0f}")
        except Exception as e:
            print(f"  ❌ Could not query contracts: {e}")

        print(f"\n  {'=' * 40}")
        if contact_count == 50 and contract_count == 25:
            print(f"  🎉 ALL DATA LOADED SUCCESSFULLY!")
        else:
            print(f"  ⚠️  Expected 50 contacts and 25 contracts.")
            print(f"  Got {contact_count} contacts and {contract_count} contracts.")
            print(f"  Check the error logs above for failed records.")
        print(f"  {'=' * 40}")


# ============================================================
# MAIN — Run everything
# ============================================================

def main():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║   VQMS — Salesforce Data Loader                  ║
    ║   Loads Vendor Contacts & Contracts via API       ║
    ╚══════════════════════════════════════════════════╝
    """)

    loader = SalesforceLoader()

    # Step 1: Login
    if not loader.login():
        print("\n❌ Cannot proceed without login. Fix credentials and try again.")
        sys.exit(1)

    # Step 2: Verify Vendor Accounts exist
    accounts_ok, vendor_map = loader.verify_accounts()
    if not accounts_ok:
        print("\n❌ Cannot proceed without Vendor Accounts. Import them first.")
        sys.exit(1)

    # Step 3: Load Contacts
    contacts_ok = loader.load_contacts(vendor_map)

    # Step 4: Load Contracts
    contracts_ok = loader.load_contracts(vendor_map)

    # Step 5: Verify
    loader.verify_data()

    print("\n✅ Done! Your VQMS data is now in Salesforce.\n")


if __name__ == "__main__":
    main()
