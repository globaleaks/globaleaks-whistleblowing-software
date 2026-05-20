from globaleaks.jobs import anomalies, \
                            cache_reset, \
                            certificate_check, \
                            cleaning, \
                            delivery, \
                            exit_nodes_refresh, \
                            notification, \
                            periodic_daily, \
                            periodic_hourly, \
                            periodic_minutely, \
                            pgp_check, \
                            update_check

jobs_list = [
    anomalies.Anomalies,
    cache_reset.CacheReset,
    certificate_check.CertificateCheck,
    cleaning.Cleaning,
    delivery.Delivery,
    exit_nodes_refresh.ExitNodesRefresh,
    notification.Notification,
    periodic_daily.PeriodicDaily,
    periodic_hourly.PeriodicHourly,
    periodic_minutely.PeriodicMinutely,
    pgp_check.PGPCheck,
    update_check.UpdateCheck,
]
