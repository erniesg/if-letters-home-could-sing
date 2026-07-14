#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define MAX_PACKET_SIZE 10485760U

#define MESSAGE_OPEN 1U
#define MESSAGE_SWIPE 2U
#define MESSAGE_STROKE 3U
#define MESSAGE_SUBMIT 4U
#define MESSAGE_RETRY 5U
#define MESSAGE_CONSENT 6U

#define MESSAGE_STATE 101U
#define MESSAGE_CONFIRM_EMPTY 102U
#define MESSAGE_ERROR 103U

#define MESSAGE_SYSTEM_TERMINATE UINT32_MAX
#define MESSAGE_SYSTEM_NEW_COORDINATOR (UINT32_MAX - 1U)

struct message_header {
    uint32_t type;
    uint32_t length;
};

struct session {
    const char *state;
    const char *consent;
    const char *heart_rate_status;
    char first_ink_at[96];
    char *strokes;
};

static const char *PURPOSE_NOTICE =
    "Heart rate can add a live rhythm to this encounter. It is optional; "
    "your reply and marginalia work the same without it.";

static const char *FIXTURE_ANNOTATIONS =
    "[{\"anchor\":{\"height\":0.18,\"width\":0.28,\"x\":0.18,\"y\":0.24},"
    "\"confidence\":0.82,\"id\":\"fixture-note-1\",\"kind\":\"reflection\","
    "\"message\":\"This reads as a warm acknowledgement. One phrase may be "
    "ambiguous; consider whether you meant care or return.\"}]";

static int send_packet(int fd, const void *contents, size_t length) {
    ssize_t sent = send(fd, contents, length, 0);
    return sent == (ssize_t)length ? 0 : -1;
}

static int send_message(int fd, uint32_t type, const char *contents) {
    size_t length = strlen(contents);
    if (length > MAX_PACKET_SIZE) {
        return -1;
    }
    struct message_header header = {type, (uint32_t)length};
    if (send_packet(fd, &header, sizeof(header)) != 0) {
        return -1;
    }
    return length == 0 ? 0 : send_packet(fd, contents, length);
}

static char *replace_once(const char *source, const char *from, const char *to) {
    const char *match = strstr(source, from);
    if (match == NULL) {
        return NULL;
    }
    size_t prefix = (size_t)(match - source);
    size_t result_length = strlen(source) - strlen(from) + strlen(to);
    char *result = malloc(result_length + 1U);
    if (result == NULL) {
        return NULL;
    }
    memcpy(result, source, prefix);
    memcpy(result + prefix, to, strlen(to));
    strcpy(result + prefix + strlen(to), match + strlen(from));
    return result;
}

static int extract_json_string(
    const char *json,
    const char *field,
    char *destination,
    size_t destination_size
) {
    char key[80];
    int key_length = snprintf(key, sizeof(key), "\"%s\":\"", field);
    if (key_length < 0 || (size_t)key_length >= sizeof(key)) {
        return -1;
    }
    const char *start = strstr(json, key);
    if (start == NULL) {
        return -1;
    }
    start += (size_t)key_length;
    const char *end = strchr(start, '"');
    if (end == NULL || end == start || (size_t)(end - start) >= destination_size) {
        return -1;
    }
    memcpy(destination, start, (size_t)(end - start));
    destination[end - start] = '\0';
    return 0;
}

static char *state_payload(const struct session *session) {
    const int reviewed = strcmp(session->state, "marginalia") == 0;
    const int submitted = reviewed || strcmp(session->state, "submitting") == 0;
    const char *annotations = reviewed ? FIXTURE_ANNOTATIONS : "[]";
    const char *review_status = reviewed ? "\"complete\"" : "null";
    const char *review_summary = reviewed
        ? "A gentle fixture reading is shown in the margin; your ink remains unchanged."
        : "";
    const char *review_id = submitted ? "\"fixture-review-0001\"" : "null";
    char *first_ink_json = NULL;
    if (session->first_ink_at[0] == '\0') {
        first_ink_json = strdup("null");
    } else if (asprintf(&first_ink_json, "\"%s\"", session->first_ink_at) < 0) {
        first_ink_json = NULL;
    }
    if (first_ink_json == NULL) {
        return NULL;
    }

    char *payload = NULL;
    int status = asprintf(
        &payload,
        "{\"annotations\":%s,\"biometricConsent\":\"%s\","
        "\"consentVersion\":\"consent-v1\",\"errorCode\":null,"
        "\"firstInkAt\":%s,\"reviewStatus\":%s,\"reviewSummary\":\"%s\","
        "\"reviewId\":%s,\"heartRateStatus\":\"%s\","
        "\"purposeNotice\":\"%s\",\"state\":\"%s\",\"strokes\":[%s]}",
        annotations,
        session->consent,
        first_ink_json,
        review_status,
        review_summary,
        review_id,
        session->heart_rate_status,
        PURPOSE_NOTICE,
        session->state,
        session->strokes
    );
    free(first_ink_json);
    return status < 0 ? NULL : payload;
}

static int send_state(int fd, const struct session *session) {
    char *payload = state_payload(session);
    if (payload == NULL) {
        return -1;
    }
    int status = send_message(fd, MESSAGE_STATE, payload);
    free(payload);
    return status;
}

static int send_error(int fd, const char *code) {
    char *payload = NULL;
    if (asprintf(
            &payload,
            "{\"code\":\"%s\",\"message\":\"The local fixture message was rejected.\"}",
            code
        ) < 0) {
        return -1;
    }
    int status = send_message(fd, MESSAGE_ERROR, payload);
    free(payload);
    return status;
}

static int append_stroke(struct session *session, const char *payload) {
    size_t length = strlen(payload);
    if (length < 2U || payload[0] != '{' || payload[length - 1U] != '}') {
        return -1;
    }
    char accepted_at[sizeof(session->first_ink_at)];
    if (extract_json_string(
            payload,
            "accepted_at",
            accepted_at,
            sizeof(accepted_at)
        ) != 0) {
        return -1;
    }
    char *with_id = replace_once(payload, "\"stroke_id\":", "\"id\":");
    if (with_id == NULL) {
        return -1;
    }
    char *normalised = replace_once(with_id, "\"accepted_at\":", "\"acceptedAt\":");
    free(with_id);
    if (normalised == NULL) {
        return -1;
    }

    char *combined = NULL;
    int status = session->strokes[0] == '\0'
        ? asprintf(&combined, "%s", normalised)
        : asprintf(&combined, "%s,%s", session->strokes, normalised);
    free(normalised);
    if (status < 0) {
        return -1;
    }
    free(session->strokes);
    session->strokes = combined;
    if (session->first_ink_at[0] == '\0') {
        strcpy(session->first_ink_at, accepted_at);
    }
    return 0;
}

static int handle_message(
    int fd,
    struct session *session,
    uint32_t type,
    const char *payload
) {
    if (type == MESSAGE_SYSTEM_NEW_COORDINATOR || type == MESSAGE_OPEN) {
        return send_state(fd, session);
    }
    if (type == MESSAGE_CONSENT) {
        char decision[16];
        if (extract_json_string(payload, "decision", decision, sizeof(decision)) != 0) {
            return send_error(fd, "invalid_message");
        }
        if (strcmp(decision, "declined") == 0) {
            session->consent = "declined";
            session->heart_rate_status = "declined";
        } else if (strcmp(decision, "granted") == 0) {
            session->consent = "granted";
            session->heart_rate_status = "unavailable";
        } else {
            return send_error(fd, "invalid_message");
        }
        return send_state(fd, session);
    }
    if (strcmp(session->consent, "pending") == 0) {
        return send_error(fd, "consent_required");
    }
    if (type == MESSAGE_SWIPE) {
        char direction[16];
        if (extract_json_string(payload, "direction", direction, sizeof(direction)) != 0) {
            return send_error(fd, "invalid_message");
        }
        if (strcmp(session->state, "incoming") == 0 && strcmp(direction, "forward") == 0) {
            session->state = "reply";
        } else if (strcmp(session->state, "reply") == 0 && strcmp(direction, "backward") == 0) {
            session->state = "incoming";
        } else {
            return send_error(fd, "invalid_transition");
        }
        return send_state(fd, session);
    }
    if (type == MESSAGE_STROKE) {
        if (strcmp(session->state, "reply") != 0 || append_stroke(session, payload) != 0) {
            return send_error(fd, "invalid_message");
        }
        return send_state(fd, session);
    }
    if (type == MESSAGE_SUBMIT) {
        if (strcmp(session->state, "reply") != 0) {
            return send_state(fd, session);
        }
        if (session->strokes[0] == '\0' && strstr(payload, "\"confirm_empty\":true") == NULL) {
            return send_message(
                fd,
                MESSAGE_CONFIRM_EMPTY,
                "{\"message\":\"Your huipi is blank. Submit it without ink?\",\"state\":\"reply\"}"
            );
        }
        session->state = "submitting";
        if (send_state(fd, session) != 0) {
            return -1;
        }
        session->state = "marginalia";
        return send_state(fd, session);
    }
    if (type == MESSAGE_RETRY) {
        session->state = "marginalia";
        return send_state(fd, session);
    }
    return send_error(fd, "unknown_message");
}

static int connect_backend(const char *path) {
    if (strlen(path) >= sizeof(((struct sockaddr_un *)0)->sun_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    int fd = socket(AF_UNIX, SOCK_SEQPACKET, 0);
    if (fd < 0) {
        return -1;
    }
    struct sockaddr_un address;
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    strcpy(address.sun_path, path);
    if (connect(fd, (struct sockaddr *)&address, sizeof(address)) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    int fd = connect_backend(argv[1]);
    if (fd < 0) {
        return 1;
    }
    struct session session = {
        .state = "incoming",
        .consent = "pending",
        .heart_rate_status = "idle",
        .first_ink_at = "",
        .strokes = strdup("")
    };
    if (session.strokes == NULL) {
        close(fd);
        return 1;
    }

    int result = 0;
    for (;;) {
        struct message_header header;
        ssize_t received = recv(fd, &header, sizeof(header), 0);
        if (received == 0) {
            break;
        }
        if (received != (ssize_t)sizeof(header) || header.length > MAX_PACKET_SIZE) {
            result = 1;
            break;
        }
        char *payload = calloc((size_t)header.length + 1U, 1U);
        if (payload == NULL) {
            result = 1;
            break;
        }
        if (header.length > 0U && recv(fd, payload, header.length, 0) != (ssize_t)header.length) {
            free(payload);
            result = 1;
            break;
        }
        if (header.type == MESSAGE_SYSTEM_TERMINATE) {
            free(payload);
            break;
        }
        if (handle_message(fd, &session, header.type, payload) != 0) {
            free(payload);
            result = 1;
            break;
        }
        free(payload);
    }
    free(session.strokes);
    close(fd);
    return result;
}
