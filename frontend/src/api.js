const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const fetchApi = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    let errorDetail = `HTTP error! status: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          errorDetail = errorData.detail.map(err => `${err.loc[1]} - ${err.msg}`).join('\n');
        } else {
          errorDetail = errorData.detail;
        }
      } else {
        errorDetail = JSON.stringify(errorData);
      }
    } catch (e) {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }
  return response.json();
};
