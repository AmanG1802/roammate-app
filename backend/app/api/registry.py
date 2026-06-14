"""
Handler registry: maps every operationId in docs/api/openapi.yaml to its Python handler.

To add a new endpoint:
  1. Add the route to docs/api/openapi.yaml with an operationId.
  2. Implement the handler in the appropriate endpoints/ module.
  3. Register it here.

spec_router.build() at startup fails immediately if any operationId is missing.
"""
from app.api.endpoints import (
    health,
    auth,
    users,
    trips,
    events,
    brainstorm,
    concierge,
    maps,
    votes,
    ideas,
    groups,
    notifications,
    dashboard,
    llm,
    billing,
    admin,
    tutorial,
)

HANDLERS = {
    # ── Health ───────────────────────────────────────────────────────────────
    "health_check":                    health.health_check,

    # ── Auth ─────────────────────────────────────────────────────────────────
    "signup":                          auth.signup,
    "verify":                          auth.verify,
    "verify_resend":                   auth.verify_resend,
    "login":                           auth.login,
    "login_with_google":               auth.login_with_google,
    "login_with_apple":                auth.login_with_apple,
    "refresh":                         auth.refresh,
    "logout":                          auth.logout,
    "password_forgot":                 auth.password_forgot,
    "password_reset":                  auth.password_reset,
    "me":                              auth.me,
    "list_identities":                 auth.list_identities,
    "unlink_identity":                 auth.unlink_identity,
    "change_email":                    auth.change_email,

    # ── Users ─────────────────────────────────────────────────────────────────
    "get_me":                          users.get_me,
    "update_me":                       users.update_me,
    "delete_me":                       users.delete_me,
    "get_personas_catalog":            users.get_personas_catalog,
    "get_my_personas":                 users.get_my_personas,
    "update_my_personas":              users.update_my_personas,

    # ── Trips ─────────────────────────────────────────────────────────────────
    "get_my_trips":                    trips.get_my_trips,
    "create_trip":                     trips.create_trip,
    "get_my_invitations":              trips.get_my_invitations,
    "accept_invitation":               trips.accept_invitation,
    "decline_invitation":              trips.decline_invitation,
    "get_trip":                        trips.get_trip,
    "update_trip":                     trips.update_trip,
    "delete_trip":                     trips.delete_trip,
    "get_idea_bin":                    trips.get_idea_bin,
    "ingest_to_idea_bin":              trips.ingest_to_idea_bin,
    "delete_idea":                     trips.delete_idea,
    "update_idea":                     trips.update_idea,
    "get_trip_members":                trips.get_trip_members,
    "invite_to_trip":                  trips.invite_to_trip,
    "update_member_role":              trips.update_member_role,
    "remove_trip_member":              trips.remove_trip_member,
    "get_trip_days":                   trips.get_trip_days,
    "add_trip_day":                    trips.add_trip_day,
    "delete_trip_day":                 trips.delete_trip_day,

    # ── Events ────────────────────────────────────────────────────────────────
    "get_events":                      events.get_events,
    "create_event":                    events.create_event,
    "update_event":                    events.update_event,
    "delete_event":                    events.delete_event,
    "move_event_to_bin":               events.move_event_to_bin,
    "trigger_ripple_engine":           events.trigger_ripple_engine,

    # ── Brainstorm ────────────────────────────────────────────────────────────
    "brainstorm_list_items":           brainstorm.list_items,
    "brainstorm_clear_items":          brainstorm.clear_items,
    "brainstorm_delete_item":          brainstorm.delete_item,
    "brainstorm_list_messages":        brainstorm.list_messages,
    "brainstorm_seed_messages":        brainstorm.seed_messages,
    "brainstorm_chat":                 brainstorm.chat,
    "brainstorm_extract":              brainstorm.extract,
    "brainstorm_bulk_insert":          brainstorm.bulk_insert,
    "brainstorm_promote":              brainstorm.promote,

    # ── Concierge ─────────────────────────────────────────────────────────────
    "concierge_chat":                  concierge.concierge_chat,
    "concierge_execute":               concierge.concierge_execute,
    "find_nearby":                     concierge.find_nearby,
    "skip_event":                      concierge.skip_event,
    "whats_next":                      concierge.whats_next,
    "today_summary":                   concierge.today_summary,
    "get_concierge_thread":            concierge.get_concierge_thread,
    "concierge_undo":                  concierge.concierge_undo,

    # ── Maps ──────────────────────────────────────────────────────────────────
    "compute_route":                   maps.compute_route,
    "get_stored_route":                maps.get_stored_route,
    "save_client_route":               maps.save_client_route,
    "re_enrich_item":                  maps.re_enrich_item,

    # ── Votes ─────────────────────────────────────────────────────────────────
    "vote_on_idea":                    votes.vote_on_idea,
    "get_idea_votes":                  votes.get_idea_votes,
    "get_idea_voters":                 votes.get_idea_voters,
    "vote_on_event":                   votes.vote_on_event,
    "get_event_votes":                 votes.get_event_votes,
    "get_event_voters":                votes.get_event_voters,

    # ── Ideas ─────────────────────────────────────────────────────────────────
    "list_idea_tags":                  ideas.list_idea_tags,
    "set_idea_tags":                   ideas.set_idea_tags,
    "copy_idea_to_trip":               ideas.copy_idea_to_trip,

    # ── Groups ────────────────────────────────────────────────────────────────
    "list_my_groups":                  groups.list_my_groups,
    "create_group":                    groups.create_group,
    "list_my_group_invitations":       groups.list_my_group_invitations,
    "accept_group_invitation":         groups.accept_group_invitation,
    "decline_group_invitation":        groups.decline_group_invitation,
    "get_group":                       groups.get_group,
    "update_group":                    groups.update_group,
    "delete_group":                    groups.delete_group,
    "list_group_members":              groups.list_group_members,
    "invite_to_group":                 groups.invite_to_group,
    "update_group_member_role":        groups.update_group_member_role,
    "remove_group_member":             groups.remove_group_member,
    "list_group_trips":                groups.list_group_trips,
    "attach_trip_to_group":            groups.attach_trip_to_group,
    "detach_trip_from_group":          groups.detach_trip_from_group,
    "get_group_idea_library":          groups.get_group_idea_library,
    "list_group_tags":                 groups.list_group_tags,

    # ── Notifications ─────────────────────────────────────────────────────────
    "list_notifications":              notifications.list_notifications,
    "unread_count":                    notifications.unread_count,
    "mark_read":                       notifications.mark_read,
    "mark_all_read":                   notifications.mark_all_read,

    # ── Dashboard ─────────────────────────────────────────────────────────────
    "get_today_widget":                dashboard.get_today_widget,

    # ── LLM ───────────────────────────────────────────────────────────────────
    "plan_trip":                       llm.plan_trip,

    # ── Billing ───────────────────────────────────────────────────────────────
    "get_billing_status":              billing.get_billing_status,
    "create_razorpay_subscription":    billing.create_razorpay_subscription,
    "create_one_time_purchase":        billing.create_one_time_purchase,
    "verify_one_time_purchase":        billing.verify_one_time_purchase,
    "razorpay_webhook":                billing.razorpay_webhook,
    "validate_coupon":                 billing.validate_coupon,
    "verify_apple_transaction":        billing.verify_apple_transaction,
    "apple_redeem_offer":              billing.apple_redeem_offer,
    "apple_server_notification":       billing.apple_server_notification,
    "cancel_subscription":             billing.cancel_subscription,

    # ── Tutorial ──────────────────────────────────────────────────────────────
    "tutorial_get_status":             tutorial.get_status,
    "tutorial_start":                  tutorial.start,
    "tutorial_patch_step":             tutorial.patch_step,
    "tutorial_skip":                   tutorial.skip,
    "tutorial_complete":               tutorial.complete,
    "tutorial_replay":                 tutorial.replay,
    "tutorial_reset":                  tutorial.reset,
    "tutorial_delete_trip":            tutorial.delete_trip,

    # ── Admin ─────────────────────────────────────────────────────────────────
    "admin_login":                     admin.admin_login,
    "list_users":                      admin.list_users,
    "token_usage_options":             admin.token_usage_options,
    "token_usage_summary":             admin.token_usage_summary,
    "token_usage_users":               admin.token_usage_users,
    "maps_usage_summary":              admin.maps_usage_summary,
    "maps_usage_users":                admin.maps_usage_users,
}
