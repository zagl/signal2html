# -*- coding: utf-8 -*-

"""Code for writing out the HTML

License: See LICENSE file.

"""

import datetime as dt
import logging
import re

from emoji import emoji_lis as emoji_list
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape
from types import SimpleNamespace as ns

from .html_colors import get_color
from .html_colors import list_colors
from .models import MMSMessageRecord
from .models import Thread
from .types import (
    DisplayType,
    get_named_message_type,
    is_inbox_type,
    is_incoming_call,
    is_joined_type,
    is_missed_call,
    is_outgoing_call,
    is_group_call,
    is_key_update,
    is_secure,
    is_group_ctrl,
)

logger = logging.getLogger(__name__)

# John Gruber's public domain url regex for web-only urls
# (https://daringfireball.net/2010/07/improved_regex_for_matching_urls)
URL_REGEX = (
    r"(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.]"
    + r"(?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|"
    + r"museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|"
    + r"ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|"
    + r"bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|"
    + r"de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|"
    + r"ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|"
    + r"ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|"
    + r"kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|"
    + r"mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|"
    + r"om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|"
    + r"sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|"
    + r"tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|"
    + r"ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+"
    + r"|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?"
    + r"\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:"
    + r"'"
    + r'".,<>?«»“”‘’])|'
    + r"(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|"
    + r"aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|"
    + r"travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|"
    + r"bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|"
    + r"ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|"
    + r"eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|"
    + r"gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|"
    + r"it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|"
    + r"lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|"
    + r"mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|"
    + r"pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|"
    + r"sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|"
    + r"to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|"
    + r"yt|yu|za|zm|zw)\b/?(?!@)))"
)


def is_all_emoji(body):
    """ Check if a message is non-empty and only contains emoji """
    body = body.replace(" ", "").replace("\ufe0f", "")
    return len(emoji_list(body)) == len(body) and len(body) > 0


def format_message(body, mentions={}):
    """Format message by processing all characters.

    - Wrap emoji in <span> for styling them
    - Escape special HTML chars
    """
    if body is None:
        return None

    emoji_pos = emoji_list(body)
    new_body = ""
    emoji_lookup = {p["location"]: p["emoji"] for p in emoji_pos}
    skip = 0
    for i, c in enumerate(body):
        if skip > 0:
            # Skip additional characters from multi-character emoji
            skip = skip - 1
        elif i in emoji_lookup:
            new_body += "<span class='msg-emoji'>%s</span>" % emoji_lookup[i]
            skip = len(emoji_lookup[i]) - 1
        elif c == "&":
            new_body += "&amp;"
        elif c == "<":
            new_body += "&lt;"
        elif c == ">":
            new_body += "&gt;"
        elif c == "\ufffc":  # Object replacement character
            mention = mentions.get(i)
            if mention:
                new_body += (
                    "<span class='msg-mention'>@%s</span>"
                    % format_message(mention.name)
                )
                skip = (
                    mention.length - 1
                )  # Not clear in what case this is not 1
            else:
                new_body += c
        else:
            new_body += c

    # Make URLs clickable
    for url in re.findall(URL_REGEX, new_body):
        if not (url.startswith("http://") or url.startswith("https://")):
            href = f"http://{url}"
        else:
            href = url
        new_body = new_body.replace(
            url, f'<a href="{href}" target="_blank">{url}</a>', 1
        )
    return new_body


def format_member_list(header: str, member_list):
    """Return a list of printable group members belonging to a category (e.g. new members)."""
    people = ns()
    people.header = header
    people.members = list()
    for member in member_list:
        designation = ""
        if not member.match_from_phone:
            if member.phone:
                designation = f"{format_message(member.name)} ({format_message(member.phone)})"
            else:
                designation = f"{format_message(member.name)}"
        else:
            if member.name is None or member.name == member.phone:
                designation = f"{format_message(member.phone)}"
            else:
                designation = f"{format_message(member.phone)} ~ {format_message(member.name)}"

        if member.admin:
            designation += " (admin)"

        people.members.append(designation)

    return people


def format_event_data_group_update(data):
    """Return a structure describing a group update event."""
    event_data = ns()
    event_data.member_lists = list()

    event_data.header = "Group update"
    if data.change_by:
        event_data.header += " by " + format_message(data.change_by.name)

    if data.group_name:
        event_data.name = data.group_name

    if data.new_members and len(data.new_members) > 0:
        member_list = format_member_list("New members:", data.new_members)
        event_data.member_lists.append(member_list)

    if data.deleted_members and len(data.deleted_members) > 0:
        member_list = format_member_list(
            "Deleted members:", data.deleted_members
        )
        event_data.member_lists.append(member_list)

    if data.members and len(data.members) > 0:
        member_list = format_member_list("Members:", data.members)
        event_data.member_lists.append(member_list)

    return event_data


def dump_thread(thread: Thread, output_dir: str):
    """Write a Thread instance to a HTML page in the output directory """

    # Combine and sort the messages
    messages = thread.mms + thread.sms
    messages.sort(key=lambda mr: mr.dateSent)

    # Find the template
    env = Environment(
        loader=PackageLoader("signal2html", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("thread.html")

    # Create the message color CSS (depends on individuals)
    group_color_css = ""
    msg_css = ".msg-sender-%i { /* recipient id: %5s */ background: %s;}\n"
    if thread.is_group:
        group_recipients = set(m.addressRecipient for m in messages)
        sender_idx = {r: k for k, r in enumerate(group_recipients)}
        colors_used = []
        group_colors = set(ar.color for ar in sender_idx)
        for ar, idx in sender_idx.items():
            if ar.isgroup:
                continue

            # ensure colors are unique, even if they're not in Signal
            ar_color = ar.color
            if ar_color in colors_used:
                color = next(
                    (c for c in list_colors() if not c in group_colors),
                    None,
                )
                ar_color = ar.color if color is None else color
            group_color_css += msg_css % (
                idx,
                ar.rid,
                get_color(ar_color),
            )
            colors_used.append(ar.color)
    else:
        # Retrieve sender info from an incoming message, if any
        firstInbox = next(
            (m for m in messages if is_inbox_type(m._type)), None
        )
        if firstInbox:
            clr = firstInbox.addressRecipient.color
            clr = "teal" if clr is None else clr
            group_color_css += msg_css % (
                0,
                firstInbox.addressRecipient.rid,
                get_color(clr),
            )

    # Create a simplified dict for each message
    prev_date = None
    simple_messages = []
    for msg in messages:

        if is_joined_type(msg._type):
            continue

        # Add a "date change" message when to mark the date
        date_sent = dt.datetime.fromtimestamp(msg.dateSent // 1000)
        date_sent = date_sent.replace(microsecond=(msg.dateSent % 1000) * 1000)
        if prev_date is None or date_sent.date() != prev_date:
            prev_date = date_sent.date()
            out = {
                "date_msg": True,
                "body": date_sent.strftime("%a, %b %d, %Y"),
            }
            simple_messages.append(out)

        # Handle event messages (calls, group changes)
        is_event = False
        event_data = None
        if is_incoming_call(msg._type):
            is_event = True
            event_data = format_message(thread.name)
        elif is_outgoing_call(msg._type):
            is_event = True
        elif is_missed_call(msg._type):
            is_event = True
        elif is_group_call(msg._type):
            is_event = True
            if msg.data is not None:
                if msg.data.initiator:
                    event_data = format_message(msg.data.initiator)
            else:
                logger.warn(f"Group call for {msg._id} without data")
        elif is_key_update(msg._type):
            is_event = True
            event_data = format_message(msg.addressRecipient.name)
        elif is_group_ctrl(msg._type):
            is_event = True
            event_data = format_event_data_group_update(
                msg.data
            )  # "Group update (v2)"

        # Deal with quoted messages
        quote = {}
        if isinstance(msg, MMSMessageRecord) and msg.quote:
            quote_author_id = msg.quote.author.rid
            quote_author_name = msg.quote.author.name
            if quote_author_id == quote_author_name:
                name = "You"
            else:
                name = quote_author_name
            quote = {
                "name": name,
                "body": format_message(msg.quote.text, msg.quote.mentions),
                "attachments": [],
            }

        # Clean up message body
        body = "" if msg.body is None else msg.body
        if isinstance(msg, MMSMessageRecord):
            all_emoji = not msg.quote and is_all_emoji(body)
        else:
            all_emoji = is_all_emoji(body)

        # Skip HTML/mentions clean-up if this is an event (formatting included in event)
        if not is_event:
            body = format_message(body, thread.mentions.get(msg._id))

        send_state = str(
            DisplayType.from_state(
                msg._type,
                msg.delivery_receipt_count > 0,
                msg.read_receipt_count > 0,
            )
        )
        send_state = send_state[
            send_state.index(".") + 1 :
        ]  # A bit hackish, StrEnum would be better (Python 3.10)

        # Create message dictionary
        aR = msg.addressRecipient
        out = {
            "isAllEmoji": all_emoji,
            "isGroup": thread.is_group,
            "isCall": is_event,
            "type": get_named_message_type(msg._type),
            "body": body,
            "event_data": event_data if is_event else None,
            "date": date_sent,
            "attachments": [],
            "id": msg._id,
            "name": aR.name,
            "secure": is_secure(msg._type) or is_event,
            "send_state": send_state,
            "delivery_receipt_count": msg.delivery_receipt_count,
            "read_receipt_count": msg.read_receipt_count,
            "sender_idx": sender_idx[aR] if thread.is_group else "0",
            "quote": quote,
            "reactions": [],
        }

        # Add attachments and reactions
        if isinstance(msg, MMSMessageRecord):
            for a in msg.attachments:
                if a.quote:
                    out["quote"]["attachments"].append(a)
                else:
                    out["attachments"].append(a)

            for r in msg.reactions:
                out["reactions"].append(
                    {
                        "recipient_id": r.recipient.rid,
                        "name": r.recipient.name,
                        "what": r.what,
                        "time_sent": r.time_sent,
                        "time_received": r.time_received,
                    }
                )

        simple_messages.append(out)

    if not simple_messages:
        return

    html = template.render(
        thread_name=thread.name,
        messages=simple_messages,
        group_color_css=group_color_css,
        date_time_format="%b %d, %H:%M",
    )
    output_file = thread.get_path(output_dir)
    with open(output_file, "w", encoding="utf-8") as fp:
        fp.write(html)
