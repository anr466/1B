import { useMemo } from 'react';
import { isAdmin } from '../utils/userUtils';

/**
 * Hook للتحقق إذا كان المستخدم أدمن
 * ✅ يستخدم user_type فقط (snake_case - موحد مع Backend)
 * ✅ يقلل التكرار في جميع الشاشات
 *
 * @param {Object} user - كائن المستخدم
 * @returns {boolean} true إذا كان المستخدم أدمن
 */
export const useIsAdmin = (user) => {
  return useMemo(() => isAdmin(user), [user]);
};

export default useIsAdmin;
