def to_spark_path(path: str) -> str:
    """
    Strips the '/lakehouse/default/' FUSE mount prefix if present so PySpark 
    can resolve the path natively against the default OneLake ABFSS root.
    """

    cleaned = path.strip()
    for prefix in ("/lakehouse/default/", "lakehouse/default/"):
        if cleaned.startswith(prefix):
            return cleaned[len(prefix):]
    return cleaned