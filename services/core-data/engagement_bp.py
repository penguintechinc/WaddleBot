"""
Engagement Module Blueprint - Extracted from engagement_module/app.py

This blueprint consolidates all engagement module routes (polls, forms) that were
originally defined as @app.route() in the engagement module.
"""
from quart import Blueprint, request, jsonify
from datetime import datetime
import sys
import os

# Make sure engagement module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../core'))

from engagement_module.app import (
    db,
    require_auth,
    check_visibility,
    hash_ip,
    format_poll,
    format_form,
    logger,
)

# Create blueprint
engagement_bp = Blueprint('engagement', __name__, url_prefix='/api/v1')


# ============================================================================
# Poll Endpoints
# ============================================================================

@engagement_bp.route('/polls', methods=['POST'])
@require_auth
async def create_poll():
    try:
        data = await request.get_json()
        community_id = data.get('community_id')
        title = data.get('title')
        options = data.get('options', [])

        if not all([community_id, title, options]):
            return jsonify({'error': 'community_id, title, and options required'}), 400

        if len(options) < 2:
            return jsonify({'error': 'At least 2 options required'}), 400

        poll_id = db.community_polls.insert(
            community_id=community_id,
            created_by=request.auth_payload.get('user_id'),
            title=title,
            description=data.get('description'),
            view_visibility=data.get('view_visibility', 'community'),
            submit_visibility=data.get('submit_visibility', 'community'),
            allow_multiple_choices=data.get('allow_multiple_choices', False),
            max_choices=data.get('max_choices', 1),
            expires_at=data.get('expires_at'),
            is_active=True
        )

        for i, opt in enumerate(options):
            db.poll_options.insert(
                poll_id=poll_id,
                option_text=opt,
                sort_order=i
            )

        db.commit()
        poll = db.community_polls[poll_id]
        opts = db(db.poll_options.poll_id == poll_id).select(orderby=db.poll_options.sort_order)

        return jsonify({
            'success': True,
            'poll': format_poll(poll, [{'id': o.id, 'text': o.option_text} for o in opts])
        }), 201

    except Exception as e:
        logger.error(f'Create poll failed: {e}', exc_info=True)
        db.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/polls/<int:poll_id>', methods=['GET'])
async def get_poll(poll_id: int):
    try:
        poll = db.community_polls[poll_id]
        if not poll:
            return jsonify({'error': 'Poll not found'}), 404

        opts = db(db.poll_options.poll_id == poll_id).select(orderby=db.poll_options.sort_order)
        options = [{'id': o.id, 'text': o.option_text} for o in opts]

        # Get vote counts
        vote_counts = {}
        for opt in opts:
            count = db(db.poll_votes.option_id == opt.id).count()
            vote_counts[opt.id] = count

        return jsonify({
            'success': True,
            'poll': format_poll(poll, options, vote_counts)
        })

    except Exception as e:
        logger.error(f'Get poll failed: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/polls/community/<int:community_id>', methods=['GET'])
async def list_polls(community_id: int):
    try:
        polls = db(
            (db.community_polls.community_id == community_id) &
            (db.community_polls.is_active == True)
        ).select(orderby=~db.community_polls.created_at)

        return jsonify({
            'success': True,
            'count': len(polls),
            'polls': [format_poll(p) for p in polls]
        })

    except Exception as e:
        logger.error(f'List polls failed: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/polls/<int:poll_id>/vote', methods=['POST'])
@require_auth
async def vote(poll_id: int):
    try:
        data = await request.get_json()
        option_ids = data.get('option_ids', [])
        user_id = request.auth_payload.get('user_id')

        poll = db.community_polls[poll_id]
        if not poll or not poll.is_active:
            return jsonify({'error': 'Poll not found or inactive'}), 404

        if poll.expires_at and poll.expires_at < datetime.utcnow():
            return jsonify({'error': 'Poll has expired'}), 400

        if not poll.allow_multiple_choices and len(option_ids) > 1:
            return jsonify({'error': 'Only one choice allowed'}), 400

        if poll.allow_multiple_choices and len(option_ids) > poll.max_choices:
            return jsonify({'error': f'Maximum {poll.max_choices} choices allowed'}), 400

        # Check if already voted
        existing = db(
            (db.poll_votes.poll_id == poll_id) &
            (db.poll_votes.user_id == user_id)
        ).select().first()

        if existing:
            return jsonify({'error': 'Already voted'}), 409

        # Record votes
        for opt_id in option_ids:
            db.poll_votes.insert(
                poll_id=poll_id,
                option_id=opt_id,
                user_id=user_id
            )

        db.commit()
        return jsonify({'success': True, 'message': 'Vote recorded'})

    except Exception as e:
        logger.error(f'Vote failed: {e}', exc_info=True)
        db.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Form Endpoints
# ============================================================================

@engagement_bp.route('/forms', methods=['POST'])
@require_auth
async def create_form():
    try:
        data = await request.get_json()
        community_id = data.get('community_id')
        title = data.get('title')
        fields = data.get('fields', [])

        if not all([community_id, title]):
            return jsonify({'error': 'community_id and title required'}), 400

        form_id = db.community_forms.insert(
            community_id=community_id,
            created_by=request.auth_payload.get('user_id'),
            title=title,
            description=data.get('description'),
            view_visibility=data.get('view_visibility', 'community'),
            submit_visibility=data.get('submit_visibility', 'community'),
            allow_anonymous=data.get('allow_anonymous', False),
            submit_once_per_user=data.get('submit_once_per_user', True),
            is_active=True
        )

        for i, field in enumerate(fields):
            db.form_fields.insert(
                form_id=form_id,
                field_type=field.get('type', 'text'),
                label=field.get('label'),
                placeholder=field.get('placeholder'),
                is_required=field.get('required', False),
                options_json=field.get('options'),
                validation_json=field.get('validation'),
                sort_order=i
            )

        db.commit()
        form = db.community_forms[form_id]

        return jsonify({
            'success': True,
            'form': format_form(form)
        }), 201

    except Exception as e:
        logger.error(f'Create form failed: {e}', exc_info=True)
        db.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/forms/<int:form_id>', methods=['GET'])
async def get_form(form_id: int):
    try:
        form = db.community_forms[form_id]
        if not form:
            return jsonify({'error': 'Form not found'}), 404

        fields = db(db.form_fields.form_id == form_id).select(orderby=db.form_fields.sort_order)
        field_list = [{
            'id': f.id,
            'type': f.field_type,
            'label': f.label,
            'placeholder': f.placeholder,
            'required': f.is_required,
            'options': f.options_json,
            'validation': f.validation_json
        } for f in fields]

        return jsonify({
            'success': True,
            'form': format_form(form, field_list)
        })

    except Exception as e:
        logger.error(f'Get form failed: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/forms/community/<int:community_id>', methods=['GET'])
async def list_forms(community_id: int):
    try:
        forms = db(
            (db.community_forms.community_id == community_id) &
            (db.community_forms.is_active == True)
        ).select(orderby=~db.community_forms.created_at)

        return jsonify({
            'success': True,
            'count': len(forms),
            'forms': [format_form(f) for f in forms]
        })

    except Exception as e:
        logger.error(f'List forms failed: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/forms/<int:form_id>/submit', methods=['POST'])
@require_auth
async def submit_form(form_id: int):
    try:
        data = await request.get_json()
        values = data.get('values', {})
        user_id = request.auth_payload.get('user_id')

        form = db.community_forms[form_id]
        if not form or not form.is_active:
            return jsonify({'error': 'Form not found or inactive'}), 404

        # Check single submission
        if form.submit_once_per_user and user_id:
            existing = db(
                (db.form_submissions.form_id == form_id) &
                (db.form_submissions.user_id == user_id)
            ).select().first()
            if existing:
                return jsonify({'error': 'Already submitted'}), 409

        # Create submission
        ip_hash = hash_ip(request.remote_addr or 'unknown')
        submission_id = db.form_submissions.insert(
            form_id=form_id,
            user_id=user_id if not form.allow_anonymous else None,
            ip_hash=ip_hash
        )

        # Save field values
        for field_id, value in values.items():
            if isinstance(value, (dict, list)):
                db.form_field_values.insert(
                    submission_id=submission_id,
                    field_id=int(field_id),
                    value_json=value
                )
            else:
                db.form_field_values.insert(
                    submission_id=submission_id,
                    field_id=int(field_id),
                    value_text=str(value)
                )

        db.commit()
        return jsonify({'success': True, 'submission_id': submission_id}), 201

    except Exception as e:
        logger.error(f'Submit form failed: {e}', exc_info=True)
        db.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/forms/<int:form_id>/submissions', methods=['GET'])
@require_auth
async def get_submissions(form_id: int):
    try:
        form = db.community_forms[form_id]
        if not form:
            return jsonify({'error': 'Form not found'}), 404

        submissions = db(db.form_submissions.form_id == form_id).select(
            orderby=~db.form_submissions.submitted_at
        )

        result = []
        for sub in submissions:
            values = db(db.form_field_values.submission_id == sub.id).select()
            result.append({
                'id': sub.id,
                'user_id': sub.user_id,
                'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                'values': {
                    str(v.field_id): v.value_json if v.value_json else v.value_text
                    for v in values
                }
            })

        return jsonify({
            'success': True,
            'count': len(result),
            'submissions': result
        })

    except Exception as e:
        logger.error(f'Get submissions failed: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500
