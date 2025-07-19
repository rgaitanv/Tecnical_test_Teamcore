## si se quiere ver en formato .csv los archivos construidos en parquet
## se utiliza este script

import pandas as pd

df = pd.read_parquet("/app/data/export/processed_log_d_chunk1.parquet")
df.to_csv("/app/data/export/processed_log_d_chunk3.csv", index=False)