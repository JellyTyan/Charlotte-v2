from utils.service_utils import get_audio_options

def get_cover_url(info_dict: dict):
    """
    Extracts the cover URL from the track's information.

    Parameters:
    ----------
    info_dict : dict
        The information dictionary for the SoundCloud track.

    Returns:
    -------
    str or None
        The URL of the cover image, or None if no appropriate image is found.
    """
    thumbnails = info_dict.get("thumbnails", [])
    return next(
        (
            thumbnail["url"]
            for thumbnail in thumbnails
            if thumbnail.get("width") == 500
        ),
        None,
    )
