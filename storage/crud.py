async def save_short_interest_record(db: AsyncSession, record: Dict[str, Any]):
    """Saves a single short interest record."""
    # This should ideally be a bulk upsert for performance.
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(ShortInterest).values(record)
    stmt = stmt.on_conflict_do_update(
        index_elements=['date', 'ticker'],
        set_=dict(
            short_volume=stmt.excluded.short_volume,
            total_volume=stmt.excluded.total_volume,
            short_volume_ratio=stmt.excluded.short_volume_ratio
        )
    )
    await db.execute(stmt)