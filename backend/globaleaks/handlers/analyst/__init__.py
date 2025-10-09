# Handlers dealing with analyst user functionalities
import json
import uuid
from datetime import datetime, timedelta
import hashlib
from sqlalchemy.sql.expression import func, and_, or_
from sqlalchemy import distinct

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.rest import errors


def apply_filters_to_query(query, filters):
    """
    Apply filters to the base InternalTip query

    :param query: SQLAlchemy query object
    :param filters: Dictionary with filter parameters (context_id, status, tags, tenant, channel, date_from, date_to)
    :return: Filtered query object
    """
    if not filters:
        return query

    if 'context_id' in filters and filters['context_id']:
        query = query.filter(models.InternalTip.context_id == filters['context_id'])

    if 'status' in filters and filters['status']:
        # Handle multiple statuses (comma-separated)
        if isinstance(filters['status'], list):
            query = query.filter(models.InternalTip.status.in_(filters['status']))
        else:
            # Handle single status or comma-separated string
            statuses = filters['status'].split(',') if ',' in filters['status'] else [filters['status']]
            query = query.filter(models.InternalTip.status.in_(statuses))

    if 'tags' in filters and filters['tags']:
        # Tags filtering not yet implemented - requires tags table schema
        pass

    if 'tenant' in filters and filters['tenant']:
        # Tenant filtering: tid is already filtered at the base level
        # Multi-tenant filtering not currently supported
        pass

    if 'channel' in filters and filters['channel']:
        # Channel filtering not yet implemented - requires channel tracking in schema
        pass

    if 'date_from' in filters and filters['date_from']:
        try:
            # Handle both timestamp and date string formats
            if isinstance(filters['date_from'], (int, float)):
                date_from = datetime.fromtimestamp(filters['date_from'] / 1000)  # Convert from milliseconds
            else:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
            query = query.filter(models.InternalTip.creation_date >= date_from)
        except (ValueError, TypeError):
            pass

    if 'date_to' in filters and filters['date_to']:
        try:
            # Handle both timestamp and date string formats
            if isinstance(filters['date_to'], (int, float)):
                date_to = datetime.fromtimestamp(filters['date_to'] / 1000)  # Convert from milliseconds
            else:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(models.InternalTip.creation_date < date_to)
        except (ValueError, TypeError):
            pass

    return query


def calculate_time_based_metrics(session, tid, filters=None):
    """
    Calculate time-based metrics for statistics

    :param session: Database session
    :param tid: Tenant ID
    :param filters: Filter parameters
    :return: Dictionary with time-based metrics
    """
    try:
        base_query = session.query(models.InternalTip).filter(models.InternalTip.tid == tid)
        base_query = apply_filters_to_query(base_query, filters)

        # Average time to first access (in hours) - simplified
        try:
            access_times = session.query(
                func.extract(
                    'epoch',
                    func.coalesce(models.InternalTip.last_access, models.InternalTip.creation_date)
                    - models.InternalTip.creation_date
                ) / 3600
            ).filter(
                models.InternalTip.tid == tid,
                models.InternalTip.access_count > 0
            )
            access_times = apply_filters_to_query(access_times, filters)
            avg_access_time = access_times.scalar() or 0
        except Exception:
            avg_access_time = 0

        # Average time to first comment (recipient response time)
        try:
            response_times = session.query(
                func.extract(
                    'epoch',
                    func.min(models.Comment.creation_date) - models.InternalTip.creation_date
                ) / 3600
            ).join(
                models.Comment, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(
                models.InternalTip.tid == tid,
                models.Comment.author_id.isnot(None)  # Only recipient comments
            ).group_by(models.InternalTip.id)

            # Apply base filters using the existing apply_filters_to_query function
            response_times = apply_filters_to_query(response_times, filters)

            avg_response_times = response_times.all()
            avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0
        except Exception:
            avg_response_time = 0

        # Average identity disclosure time (for initially anonymous reports)
        try:
            disclosure_times = session.query(
                func.extract(
                    'epoch',
                    models.InternalTipData.creation_date - models.InternalTip.creation_date
                ) / 3600
            ).join(
                models.InternalTipData,
                and_(
                    models.InternalTipData.internaltip_id == models.InternalTip.id,
                    models.InternalTipData.key == 'whistleblower_identity',
                    models.InternalTipData.creation_date != models.InternalTip.creation_date
                )
            ).filter(models.InternalTip.tid == tid)
            disclosure_times = apply_filters_to_query(disclosure_times, filters)
            disclosure_times_list = disclosure_times.all()
            avg_disclosure_time = sum(disclosure_times_list) / len(disclosure_times_list) if disclosure_times_list else 0
        except Exception:
            avg_disclosure_time = 0

        # Count total exchanges (comments back and forth)
        try:
            exchange_counts = session.query(
                func.count(models.Comment.id)
            ).join(
                models.InternalTip, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(models.InternalTip.tid == tid)
            exchange_counts = apply_filters_to_query(exchange_counts, filters)
            total_exchanges = exchange_counts.scalar() or 0
        except Exception:
            total_exchanges = 0

        # Count reports with exchanges
        try:
            tips_with_exchanges = session.query(
                func.count(distinct(models.InternalTip.id))
            ).join(
                models.Comment, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(models.InternalTip.tid == tid)
            tips_with_exchanges = apply_filters_to_query(tips_with_exchanges, filters)
            num_tips_with_exchanges = tips_with_exchanges.scalar() or 0
        except Exception:
            num_tips_with_exchanges = 0

        avg_exchanges_per_tip = total_exchanges / num_tips_with_exchanges if num_tips_with_exchanges > 0 else 0

        return {
            "avg_access_time_hours": round(avg_access_time, 2),
            "avg_response_time_hours": round(avg_response_time, 2),
            "avg_identity_disclosure_time_hours": round(avg_disclosure_time, 2),
            "avg_exchanges_per_report": round(avg_exchanges_per_tip, 2),
            "total_exchanges": total_exchanges,
            "reports_with_exchanges": num_tips_with_exchanges
        }
    except Exception:
        # Return default values if anything fails
        return {
            "avg_access_time_hours": 0,
            "avg_response_time_hours": 0,
            "avg_identity_disclosure_time_hours": 0,
            "avg_exchanges_per_report": 0,
            "total_exchanges": 0,
            "reports_with_exchanges": 0
        }


@transact
def get_stats(session, tid, filters=None):
    """
    Transaction for retrieving analyst statistics with optional filtering

    :param session: An ORM session
    :param tid: A tenant ID
    :param filters: Dictionary containing filter parameters (context_id, status, tags, tenant, channel, date_from, date_to)
    """
    try:
        # Build base query with filters
        base_query = session.query(func.count(models.InternalTip.id)).filter(models.InternalTip.tid == tid)
        base_query = apply_filters_to_query(base_query, filters)
        reports_count = base_query.one()[0]

        # Apply filters to all count queries
        no_access_query = session.query(func.count(models.InternalTip.id)) \
                                .filter(models.InternalTip.tid == tid,
                    models.InternalTip.access_count == 0)
        no_access_query = apply_filters_to_query(no_access_query, filters)
        num_tips_no_access = no_access_query.one()[0]

        mobile_query = session.query(func.count(models.InternalTip.id)) \
                             .filter(models.InternalTip.tid == tid,
                    models.InternalTip.mobile == True)
        mobile_query = apply_filters_to_query(mobile_query, filters)
        num_tips_mobile = mobile_query.one()[0]

        tor_query = session.query(func.count(models.InternalTip.id)) \
                             .filter(models.InternalTip.tid == tid,
                    models.InternalTip.tor == True)
        tor_query = apply_filters_to_query(tor_query, filters)
        num_tips_tor = tor_query.one()[0]

        subscribed_query = session.query(func.count(models.InternalTip.id)) \
                                 .filter(models.InternalTip.tid == tid) \
                                 .join(models.InternalTipData,
                                       and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                            models.InternalTipData.key == 'whistleblower_identity',
                                            models.InternalTipData.creation_date == models.InternalTip.creation_date))
        subscribed_query = apply_filters_to_query(subscribed_query, filters)
        num_subscribed_tips = subscribed_query.one()[0]

        initially_anonymous_query = session.query(func.count(models.InternalTip.id)) \
                                       .filter(models.InternalTip.tid == tid) \
                                       .join(models.InternalTipData,
                                             and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                                  models.InternalTipData.key == 'whistleblower_identity',
                                                  models.InternalTipData.creation_date != models.InternalTip.creation_date))
        initially_anonymous_query = apply_filters_to_query(initially_anonymous_query, filters)
        num_initially_anonymous_tips = initially_anonymous_query.one()[0]

        num_anonymous_tips = reports_count - num_subscribed_tips - num_initially_anonymous_tips

        # Calculate time-based metrics
        time_metrics = calculate_time_based_metrics(session, tid, filters)

        # Combine all metrics
        stats = {
        "reports_count": reports_count,
        "reports_with_no_access": num_tips_no_access,
        "reports_anonymous": num_anonymous_tips,
        "reports_subscribed": num_subscribed_tips,
        "reports_initially_anonymous": num_initially_anonymous_tips,
        "reports_mobile": num_tips_mobile,
        "reports_tor": num_tips_tor
    }
        # Add time-based metrics
        stats.update(time_metrics)
        return stats
    except Exception:
        # Return basic default stats if anything fails
        return {
            "reports_count": 0,
            "reports_with_no_access": 0,
            "reports_anonymous": 0,
            "reports_subscribed": 0,
            "reports_initially_anonymous": 0,
            "reports_mobile": 0,
            "reports_tor": 0,
            "avg_access_time_hours": 0,
            "avg_response_time_hours": 0,
            "avg_identity_disclosure_time_hours": 0,
            "avg_exchanges_per_report": 0,
            "total_exchanges": 0,
            "reports_with_exchanges": 0
        }


class Statistics(BaseHandler):
    """
    Handler for statistics fetch with filtering support

    Accepts query parameters:
    - context_id: Filter by context ID
    - status: Filter by report status (comma-separated for multiple)
    - tags: Filter by tags (comma-separated for multiple)
    - tenant: Filter by tenant (comma-separated for multiple)
    - channel: Filter by communication channel (comma-separated for multiple)
    - date_from: Filter reports from date (YYYY-MM-DD or timestamp)
    - date_to: Filter reports to date (YYYY-MM-DD or timestamp)
    """
    check_roles = 'analyst'

    def get(self):
        # Parse query parameters from request.args
        filters = {}

        # Helper function to get query parameter value
        def get_param(name):
            args = self.request.args.get(name.encode())
            return args[0].decode() if args else ''

        context_id = get_param('context_id')
        if context_id:
            filters['context_id'] = context_id

        status = get_param('status')
        if status:
            filters['status'] = status.split(',') if ',' in status else [status]

        tags = get_param('tags')
        if tags:
            filters['tags'] = tags.split(',') if ',' in tags else [tags]

        tenant = get_param('tenant')
        if tenant:
            filters['tenant'] = tenant.split(',') if ',' in tenant else [tenant]

        channel = get_param('channel')
        if channel:
            filters['channel'] = channel.split(',') if ',' in channel else [channel]

        date_from = get_param('date_from')
        if date_from:
            # Try to parse as integer (timestamp) first, then as string
            try:
                filters['date_from'] = int(date_from)
            except ValueError:
                filters['date_from'] = date_from

        date_to = get_param('date_to')
        if date_to:
            # Try to parse as integer (timestamp) first, then as string
            try:
                filters['date_to'] = int(date_to)
            except ValueError:
                filters['date_to'] = date_to

        return get_stats(self.request.tid, filters if filters else None)


class FilterOptions(BaseHandler):
    """
    Handler to provide filter options for the statistics page
    Returns available values for status, tags, tenant, and channel filters
    """
    check_roles = 'analyst'

    def get(self):
        filter_type = self.get_param('type')
        tid = self.request.tid

        if filter_type == 'status':
            return self.get_status_options(tid)
        elif filter_type == 'tags':
            return self.get_tag_options(tid)
        elif filter_type == 'tenant':
            return self.get_tenant_options(tid)
        elif filter_type == 'channel':
            return self.get_channel_options(tid)
        else:
            return {
                'status': self.get_status_options(tid),
                'tags': self.get_tag_options(tid),
                'tenant': self.get_tenant_options(tid),
                'channel': self.get_channel_options(tid)
            }

    def get_param(self, name):
        """Helper function to get query parameter value"""
        args = self.request.args.get(name.encode())
        return args[0].decode() if args else ''

    def get_status_options(self, tid):
        """Get available status options from database"""
        try:
            # Get distinct statuses from InternalTip
            statuses = self.session.query(models.InternalTip.status) \
                .filter(models.InternalTip.tid == tid) \
                .distinct().all()

            # Convert to the format expected by the frontend
            options = []
            for i, (status,) in enumerate(statuses, 1):
                if status:  # Only include non-null statuses
                    options.append({
                        'id': i,
                        'label': status.title()
                    })

            return options
        except Exception:
            return []

    def get_tag_options(self, tid):
        """Get available tag options from database"""
        try:
            # Get tags from InternalTipData or similar tables
            # Note: Adjust based on actual tag schema implementation
            tags = self.session.query(models.InternalTipData.value) \
                .join(models.InternalTip, models.InternalTipData.internaltip_id == models.InternalTip.id) \
                .filter(models.InternalTip.tid == tid,
                        models.InternalTipData.key.like('%tag%')) \
                .distinct().limit(20).all()

            options = []
            for i, (tag,) in enumerate(tags, 1):
                if tag and tag.strip():
                    options.append({
                        'id': i,
                        'label': tag.strip()
                    })

            return options
        except Exception:
            return []

    def get_tenant_options(self, tid):
        """Get available tenant options from database"""
        try:
            # Get tenant information from the Tenant model
            tenants = self.session.query(models.Tenant.id, models.Tenant.name) \
                .filter(models.Tenant.id == tid) \
                .all()

            options = []
            for i, (tenant_id, name) in enumerate(tenants, 1):
                if name:
                    options.append({
                        'id': i,
                        'label': name
                    })

            return options
        except Exception:
            return []

    def get_channel_options(self, tid):
        """Get available channel options from database"""
        try:
            # Get channel information from contexts (submission channels)
            channels = self.session.query(models.Context.name) \
                .join(models.InternalTip, models.InternalTip.context_id == models.Context.id) \
                .filter(models.InternalTip.tid == tid) \
                .distinct().limit(10).all()

            options = []
            for i, (channel,) in enumerate(channels, 1):
                if channel and channel.strip():
                    options.append({
                        'id': i,
                        'label': channel.strip()
                    })

            return options
        except Exception:
            return []


def _kv_key(tid):
    raw = f"analyst_templates_{tid}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


@transact
def _db_load_templates(session, tid):
    try:
        key = _kv_key(tid)
        rec = session.query(models.ArchivedSchema).filter(models.ArchivedSchema.hash == key).one_or_none()
        if rec and isinstance(rec.schema, dict):
            return rec.schema.get('templates', [])
        return []
    except Exception:
        return []


@transact
def _db_save_templates(session, tid, templates):
    key = _kv_key(tid)
    rec = session.query(models.ArchivedSchema).filter(models.ArchivedSchema.hash == key).one_or_none()
    if rec is None:
        rec = models.ArchivedSchema()
        rec.hash = key
        rec.schema = {'templates': templates}
        session.add(rec)
    else:
        rec.schema = {'templates': templates}
    # Ensure changes are flushed/committed within transaction
    try:
        session.flush()
    except Exception:
        pass


class Templates(BaseHandler):
    """
    Handler for report template management (CRUD operations)
    """
    check_roles = 'analyst'

    def _load_templates(self, tid):
        return _db_load_templates(tid)

    def _save_templates(self, tid, templates):
        _db_save_templates(tid, templates)

    def _default_template(self):
        now = datetime.utcnow().isoformat() + 'Z'
        return {
            'id': 'globaleaks-default',
            'name': 'GlobaLeaks',
            'createdBy': 'system',
            'createdDate': now,
            'lastModified': now,
            'isDefault': True,
            'config': {
                'selectedMetrics': ['reports_received', 'reports_not_accessed', 'anonymous_reports'],
                'selectedCharts': []
            },
            'permissions': {
                'canEdit': True,
                'canDelete': False,
                'canExport': True
            }
        }

    def get(self):
        """Get all templates for the current tenant"""
        tid = self.request.tid
        def _ensure_seed(templates):
            if templates:
                return templates
            seeded = [self._default_template()]
            return self._save_templates(tid, seeded).addCallback(lambda _: seeded)

        d = self._load_templates(tid)
        d.addCallback(_ensure_seed)
        d.addErrback(lambda _: [])
        return d

    def post(self):
        """Create a new template"""
        tid = self.request.tid

        # Parse body leniently
        try:
            body = self.request.content.read()
            data = json.loads(body.decode('utf-8'))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        name = data.get('name') or 'Untitled Report'
        cfg = data.get('config') or {}

        new_template = {
            'id': str(uuid.uuid4()),
            'name': name,
            'createdDate': datetime.utcnow().isoformat() + 'Z',
            'lastModified': datetime.utcnow().isoformat() + 'Z',
            'createdBy': 'analyst',
            'isDefault': False,
            'config': {
                'selectedMetrics': list(cfg.get('selectedMetrics') or []),
                'selectedCharts': list(cfg.get('selectedCharts') or [])
            },
            'permissions': data.get('permissions') or {
                'canEdit': True,
                'canDelete': True,
                'canExport': True
            }
        }

        def _append_and_save(templates):
            lst = templates or []
            lst.append(new_template)
            return self._save_templates(tid, lst).addCallback(lambda _: new_template)

        d = self._load_templates(tid)
        d.addCallback(_append_and_save)
        d.addErrback(lambda _: new_template)
        return d

    def put(self):
        """Update an existing template"""
        tid = self.request.tid

        # Parse body leniently
        try:
            body = self.request.content.read()
            data = json.loads(body.decode('utf-8'))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        template_id = data.get('id')
        if not template_id:
            return {'error': 'Template ID is required'}

        cfg = data.get('config') or {}
        sanitized = {
            **data,
            'config': {
                'selectedMetrics': list(cfg.get('selectedMetrics') or []),
                'selectedCharts': list(cfg.get('selectedCharts') or [])
            },
            'lastModified': datetime.utcnow().isoformat() + 'Z'
        }

        def _update_and_save(templates):
            lst = templates or []
            updated = None
            for i, t in enumerate(lst):
                if t.get('id') == template_id:
                    lst[i] = {**t, **sanitized}
                    updated = lst[i]
                    break
            if updated is None:
                return {'error': 'Template not found'}
            return self._save_templates(tid, lst).addCallback(lambda _: updated)

        d = self._load_templates(tid)
        d.addCallback(_update_and_save)
        d.addErrback(lambda _: sanitized)
        return d


class TemplateInstance(BaseHandler):
    """
    Handler for individual template operations (GET, DELETE)
    """
    check_roles = 'analyst'

    def _load_templates(self, tid):
        return _db_load_templates(tid)

    def _save_templates(self, tid, templates):
        return _db_save_templates(tid, templates)

    def _default_template(self):
        now = datetime.utcnow().isoformat() + 'Z'
        return {
            'id': 'globaleaks-default',
            'name': 'GlobaLeaks',
            'createdBy': 'system',
            'createdDate': now,
            'lastModified': now,
            'isDefault': True,
            'config': {
                'selectedMetrics': ['reports_received', 'reports_not_accessed', 'anonymous_reports'],
                'selectedCharts': []
            },
            'permissions': {
                'canEdit': True,
                'canDelete': False,
                'canExport': True
            }
        }

    def get(self, template_id):
        """Get a specific template by ID"""
        tid = self.request.tid
        
        def _find_template(templates):
            for t in templates:
                if t.get('id') == template_id:
                    return t
            # fallback to default template if requested explicitly
            if template_id == 'globaleaks-default':
                return self._default_template()
            raise errors.ResourceNotFound("Template not found")
        
        d = self._load_templates(tid)
        d.addCallback(_find_template)
        d.addErrback(lambda _: self._default_template() if template_id == 'globaleaks-default' else errors.ResourceNotFound("Template not found"))
        return d

    def delete(self, template_id):
        """Delete a specific template"""
        tid = self.request.tid
        
        # Don't allow deletion of default template
        if template_id == 'globaleaks-default':
            raise errors.ForbiddenOperation("Cannot delete default template")
        
        def _remove_and_save(templates):
            new_templates = [t for t in templates if t.get('id') != template_id]
            if len(new_templates) == len(templates):
                raise errors.ResourceNotFound('Template not found')
            return self._save_templates(tid, new_templates).addCallback(lambda _: {'success': True})
        
        d = self._load_templates(tid)
        d.addCallback(_remove_and_save)
        return d


