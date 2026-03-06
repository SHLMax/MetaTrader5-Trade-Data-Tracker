import asyncio
from database import daily_summary_collection

async def main():
    res = await daily_summary_collection.delete_many({})
    print(f"Deleted {res.deleted_count} records")

if __name__ == "__main__":
    asyncio.run(main())
