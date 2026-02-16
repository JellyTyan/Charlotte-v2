import logging
import re

from curl_cffi.requests import AsyncSession

from models.errors import BotError, ErrorCode

logger = logging.getLogger(__name__)


async def get_guest_token(auth: str, client: AsyncSession) -> str:
    """Get a guest token from Twitter API."""
    guest_token_url = "https://api.twitter.com/1.1/guest/activate.json"
    headers = {"Authorization": auth}

    response = await client.post(guest_token_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("guest_token")
    else:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get guest token. Status code: {response.status_code}",
            is_logged=True
        )


async def get_tweet_info(
    tweet_id: int,
    auth: str,
    guest_token: str,
    client: AsyncSession,
    retry: bool = True,
    csrf_token: str | None = None,
    auth_token: str | None = None
) -> dict:
    """Get tweet information from Twitter API."""
    premium = bool(csrf_token and auth_token)

    if premium:
        if auth_token and csrf_token:
            client.cookies.set("auth_token", auth_token, domain=".x.com")
            client.cookies.set("ct0", csrf_token, domain=".x.com")
            headers = {
                "Authorization": auth,
                "Content-Type": "application/json",
                "x-csrf-token": csrf_token,
            }
            params = {
                "variables": f'{{"tweetId":"{tweet_id}","includePromotedContent":true,"withBirdwatchNotes":true,"withVoice":true,"withCommunity":true}}',
                'features': '{"creator_subscriptions_tweet_preview_api_enabled":true,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"responsive_web_grok_annotations_enabled":false,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":true,"post_ctas_fetch_enabled":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"responsive_web_profile_redirect_enabled":false,"rweb_tipjar_consumption_enabled":false,"verified_phone_label_enabled":false,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_imagine_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_enhance_cards_enabled":false}',
                'fieldToggles': '{"withArticleRichContentState":true,"withArticlePlainText":false}',
            }
            tweet_info_url = "https://x.com/i/api/graphql/0aTrQMKgj95K791yXeNDRA/TweetResultByRestId"
    else:
        client.cookies.set("gt", guest_token, domain=".x.com")
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "X-Guest-Token": guest_token,
        }
        params = {
            "variables": f'{{"tweetId":"{tweet_id}","withCommunity":false,"includePromotedContent":false,"withVoice":false}}',
            'features': '{"creator_subscriptions_tweet_preview_api_enabled":true,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":false,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_enhance_cards_enabled":false}',
        }
        tweet_info_url = "https://api.x.com/graphql/SAvsJgT-uo2NRaJBVX9-Hg/TweetResultByRestId"

    try:
        response = await client.get(tweet_info_url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            if retry and not premium:
                logger.warning(f"Tweet info request failed with status {response.status_code}, regenerating token and retrying")
                new_guest_token = await get_guest_token(auth, client)
                return await get_tweet_info(tweet_id, auth, new_guest_token, client, retry=False, csrf_token=csrf_token, auth_token=auth_token)
            else:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=f"Failed to get tweet info: response status {response.status_code}",
                    url=str(tweet_id),
                    is_logged=True
                )
    except BotError:
        raise
    except Exception as e:
        if retry and not premium:
            logger.warning(f"Tweet info request failed with error {e}, regenerating token and retrying")
            new_guest_token = await get_guest_token(auth, client)
            return await get_tweet_info(tweet_id, auth, new_guest_token, client, retry=False, csrf_token=csrf_token, auth_token=auth_token)
        else:
            raise


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)
