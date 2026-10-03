/**
 * Formats API errors (including FastAPI/Pydantic validation errors) into safe,
 * user-friendly strings to avoid React error #31 (rendering objects in JSX).
 */
export function formatApiError(
  err: any,
  fallbackMessage = 'An unexpected error occurred. Please try again.'
): string {
  if (!err) {
    return fallbackMessage;
  }

  // 1. If error is already a string
  if (typeof err === 'string') {
    return err;
  }

  // 2. Check response data
  const data = err.response?.data;

  if (data) {
    const detail = data.detail;

    // String detail
    if (typeof detail === 'string') {
      return detail;
    }

    // Array of Pydantic validation errors: [{ type, loc, msg, input, ctx }]
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const cleanMsg = item.msg
              ? item.msg.replace(/^Value error,\s*/i, '')
              : null;
            if (cleanMsg) {
              const field =
                Array.isArray(item.loc) && item.loc.length > 1
                  ? item.loc[item.loc.length - 1]
                  : null;
              if (
                field &&
                typeof field === 'string' &&
                !['body', 'query', 'path'].includes(field)
              ) {
                return `${field}: ${cleanMsg}`;
              }
              return cleanMsg;
            }
            if (item.message && typeof item.message === 'string') {
              return item.message;
            }
            return JSON.stringify(item);
          }
          return String(item);
        })
        .filter(Boolean);

      if (messages.length > 0) {
        return messages.join('; ');
      }
    }

    // Object detail: { msg: '...' } or { message: '...' }
    if (detail && typeof detail === 'object') {
      if (typeof detail.msg === 'string') {
        return detail.msg.replace(/^Value error,\s*/i, '');
      }
      if (typeof detail.message === 'string') {
        return detail.message;
      }
    }

    // Other potential message fields on data
    if (typeof data.message === 'string') return data.message;
    if (typeof data.error === 'string') return data.error;
  }

  // 3. Network or connection errors
  if (err.message) {
    if (err.message === 'Network Error' || err.code === 'ERR_NETWORK') {
      return 'Unable to connect to server. Please check your internet connection.';
    }
    return String(err.message);
  }

  return fallbackMessage;
}
