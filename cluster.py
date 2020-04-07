from dask.distributed import Client
from dask.distributed import LocalCluster

LOCAL_DASK_DASHBOARD = 10000

print(f'starting dask cluster on port {LOCAL_DASK_DASHBOARD}')
cluster = LocalCluster(dashboard_address=f':{LOCAL_DASK_DASHBOARD}')
client = Client(cluster)
