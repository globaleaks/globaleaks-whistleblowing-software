from globaleaks.jobs import anomalies, \
                            cache_reset, \
                            certificate_check, \
                            cleaning, \
                            delivery, \
                            exit_nodes_refresh, \
                            notification, \
                            pgp_check, \
                            session_management, \
                            statistics, \
                            update_check, \
                            backup

jobs_list = [
    anomalies.Anomalies,
    cache_reset.CacheReset,
    certificate_check.CertificateCheck,
    cleaning.Cleaning,
    delivery.Delivery,
    exit_nodes_refresh.ExitNodesRefresh,
    notification.Notification,
    pgp_check.PGPCheck,
    session_management.SessionManagement,
    statistics.Statistics,
    update_check.UpdateCheck,
    backup.Backup
]
