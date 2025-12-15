export const formatReportTime = (dateStr?: string): string => {
    if (!dateStr) return '';

    try {
        const date = new Date(dateStr);
        const now = new Date();

        // Check if valid date
        if (isNaN(date.getTime())) {
            return dateStr; // Fallback to original string if parsing fails
        }

        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');

        const currentYear = now.getFullYear();

        if (year === currentYear) {
            return `${month}-${day} ${hours}:${minutes}`;
        } else {
            return `${year}-${month}-${day} ${hours}:${minutes}`;
        }
    } catch (e) {
        return dateStr;
    }
};
