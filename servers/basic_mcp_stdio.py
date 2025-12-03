import csv
import logging
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("ExpensesMCP")


SCRIPT_DIR = Path(__file__).parent
EXPENSES_FILE = SCRIPT_DIR / "expenses.csv"


mcp = FastMCP("Expenses Tracker")


class PaymentMethod(Enum):
    AMEX = "amex"
    VISA = "visa"
    CASH = "cash"


class Category(Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    GADGET = "gadget"
    OTHER = "other"


@mcp.tool
async def add_expense(
    date: Annotated[date, "Date of the expense in YYYY-MM-DD format"],
    amount: Annotated[float, "Positive numeric amount of the expense"],
    category: Annotated[Category, "Category label"],
    description: Annotated[str, "Human-readable description of the expense"],
    payment_method: Annotated[PaymentMethod, "Payment method used"],
):
    """Add a new expense to the expenses.csv file."""
    if amount <= 0:
        return "Error: Amount must be positive"

    date_iso = date.isoformat()
    logger.info(f"Adding expense: ${amount} for {description} on {date_iso}")

    try:
        file_exists = EXPENSES_FILE.exists()

        with open(EXPENSES_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(["date", "amount", "category", "description", "payment_method"])

            writer.writerow([date_iso, amount, category.value, description, payment_method.value])

        return f"Successfully added expense: ${amount} for {description} on {date_iso}"

    except Exception as e:
        logger.error(f"Error adding expense: {str(e)}")
        return "Error: Unable to add expense"


@mcp.resource("resource://expenses")
async def get_expenses_data():
    """Get raw expense data from CSV file"""
    logger.info("Expenses data accessed")

    try:
        with open(EXPENSES_FILE, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            expenses_data = list(reader)

        csv_content = f"Expense data ({len(expenses_data)} entries):\n\n"
        for expense in expenses_data:
            csv_content += (
                f"Date: {expense['date']}, "
                f"Amount: ${expense['amount']}, "
                f"Category: {expense['category']}, "
                f"Description: {expense['description']}, "
                f"Payment: {expense['payment_method']}\n"
            )

        return csv_content

    except FileNotFoundError:
        logger.error("Expenses file not found")
        return "Error: Expense data unavailable"
    except Exception as e:
        logger.error(f"Error reading expenses: {str(e)}")
        return "Error: Unable to retrieve expense data"


@mcp.prompt
def analyze_spending_prompt(
    category: str | None = None, start_date: str | None = None, end_date: str | None = None
) -> str:
    """Generate a prompt to analyze spending patterns with optional filters."""

    filters = []
    if category:
        filters.append(f"Category: {category}")
    if start_date:
        filters.append(f"From: {start_date}")
    if end_date:
        filters.append(f"To: {end_date}")

    filter_text = f" ({', '.join(filters)})" if filters else ""

    return f"""
    Please analyze my spending patterns{filter_text} and provide:

    1. Total spending breakdown by category
    2. Average daily/weekly spending
    3. Most expensive single transaction
    4. Payment method distribution
    5. Spending trends or unusual patterns
    6. Recommendations for budget optimization

    Use the expense data to generate actionable insights.
    """


if __name__ == "__main__":
    logger.info("MCP Expenses server starting")
    mcp.run()
