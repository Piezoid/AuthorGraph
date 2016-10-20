import logging
logger = logging.getLogger(__name__)

def get_pages(pages):
    if not pages:
        return (None, None)
    else:
        pages = pages.replace('–', '-')
        pages = pages.replace(' ', '-')
        try:
            ps = [int(i) for i in pages.split('-') if i]
        except ValueError:
            logger.warning('Unknown page range format : %r' % pages)
            return (None, None)

        if len(ps) == 1:
            return (ps[0], None)
        elif len(ps) == 2:
            return (ps[0], ps[1])
        else:
            logger.warning('Unknown page range format : %r' % pages)
            return (None, None)
