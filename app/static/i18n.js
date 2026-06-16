// ===== Bilingual string dictionary (RU / UZ) =====
(function () {
  const STRINGS = {
    ru: {
      app_title: "Финансы",
      tab_report: "Отчёт",
      tab_debts: "Долги",
      update: "Обновить",
      lang_name: "RU",

      ring_spent: "ПОТРАЧЕНО",
      ring_no_data: "Нет данных за {month}",
      ring_no_data_plain: "Нет данных",
      ring_add_first: "Добавьте первый расход",
      ring_no_income: "Доход не указан",
      pct_income: "{pct}% дохода",
      saved: "Отложено",
      overspend: "Перерасход",
      income: "Доход",

      categories_title: "РАСХОДЫ ПО КАТЕГОРИЯМ",
      no_expenses: "Нет расходов за этот месяц.",

      seg_expense: "Расход",
      seg_income: "Доход",
      f_category: "Категория",
      f_amount: "Сумма (сум)",
      f_date: "Дата",
      f_note: "Заметка",
      f_income_type: "Тип дохода",
      optional: "необязательно",
      save: "Сохранить",
      saved_ok: "Сохранено.",

      history_title: "ИСТОРИЯ",
      no_records: "Записей нет.",
      cancel: "Отмена",
      confirm_delete: "Удалить запись?",
      deleted: "Удалено.",
      entry_expense: "Расход",
      entry_income: "Доход",

      err_load_categories: "Не удалось загрузить категории.",
      err_load_income: "Не удалось загрузить типы дохода.",
      err_load_summary: "Не удалось загрузить сводку.",
      err_load_history: "Не удалось загрузить историю.",
      err_save_expense: "Не удалось сохранить расход.",
      err_save_income: "Не удалось сохранить доход.",
      err_delete: "Не удалось удалить.",
      err_save_changes: "Не удалось сохранить изменения.",

      // Debts
      debts_net: "Чистый баланс",
      they_owe: "Мне должны",
      i_owe: "Я должен",
      group_lent: "МНЕ ДОЛЖНЫ",
      group_borrowed: "Я ДОЛЖЕН",
      add_lent: "Я дал в долг",
      add_borrowed: "Я взял в долг",
      debt_person: "Имя",
      debt_outstanding: "осталось",
      debt_of: "из",
      add_repayment: "Платёж",
      settle: "Закрыть",
      settled_badge: "Закрыт",
      no_debts_lent: "Вам никто не должен.",
      no_debts_borrowed: "Вы никому не должны.",
      repayment_amount: "Сумма платежа",
      add: "Добавить",
      confirm_delete_debt: "Удалить долг?",
      confirm_delete_repayment: "Удалить платёж?",
      err_load_debts: "Не удалось загрузить долги.",
      err_save_debt: "Не удалось сохранить долг.",
      err_repayment: "Сумма больше остатка долга.",
    },
    uz: {
      app_title: "Moliya",
      tab_report: "Hisobot",
      tab_debts: "Qarzlar",
      update: "Yangilash",
      lang_name: "UZ",

      ring_spent: "SARFLANDI",
      ring_no_data: "{month} uchun ma'lumot yo'q",
      ring_no_data_plain: "Ma'lumot yo'q",
      ring_add_first: "Birinchi xarajatni qo'shing",
      ring_no_income: "Daromad ko'rsatilmagan",
      pct_income: "daromadning {pct}%",
      saved: "Jamg'arildi",
      overspend: "Ortiqcha sarf",
      income: "Daromad",

      categories_title: "TOIFALAR BO'YICHA XARAJAT",
      no_expenses: "Bu oyda xarajat yo'q.",

      seg_expense: "Xarajat",
      seg_income: "Daromad",
      f_category: "Toifa",
      f_amount: "Summa (so'm)",
      f_date: "Sana",
      f_note: "Izoh",
      f_income_type: "Daromad turi",
      optional: "ixtiyoriy",
      save: "Saqlash",
      saved_ok: "Saqlandi.",

      history_title: "TARIX",
      no_records: "Yozuvlar yo'q.",
      cancel: "Bekor qilish",
      confirm_delete: "Yozuv o'chirilsinmi?",
      deleted: "O'chirildi.",
      entry_expense: "Xarajat",
      entry_income: "Daromad",

      err_load_categories: "Toifalarni yuklab bo'lmadi.",
      err_load_income: "Daromad turlarini yuklab bo'lmadi.",
      err_load_summary: "Hisobotni yuklab bo'lmadi.",
      err_load_history: "Tarixni yuklab bo'lmadi.",
      err_save_expense: "Xarajatni saqlab bo'lmadi.",
      err_save_income: "Daromadni saqlab bo'lmadi.",
      err_delete: "O'chirib bo'lmadi.",
      err_save_changes: "O'zgarishlarni saqlab bo'lmadi.",

      // Debts
      debts_net: "Sof balans",
      they_owe: "Menga qarzdor",
      i_owe: "Men qarzdorman",
      group_lent: "MENGA QARZDOR",
      group_borrowed: "MEN QARZDORMAN",
      add_lent: "Qarz berdim",
      add_borrowed: "Qarz oldim",
      debt_person: "Ism",
      debt_outstanding: "qoldi",
      debt_of: "/",
      add_repayment: "To'lov",
      settle: "Yopish",
      settled_badge: "Yopildi",
      no_debts_lent: "Sizga hech kim qarzdor emas.",
      no_debts_borrowed: "Siz hech kimga qarzdor emassiz.",
      repayment_amount: "To'lov summasi",
      add: "Qo'shish",
      confirm_delete_debt: "Qarz o'chirilsinmi?",
      confirm_delete_repayment: "To'lov o'chirilsinmi?",
      err_load_debts: "Qarzlarni yuklab bo'lmadi.",
      err_save_debt: "Qarzni saqlab bo'lmadi.",
      err_repayment: "Summa qarz qoldig'idan ko'p.",
    },
  };

  let lang = localStorage.getItem("lang") || "ru";

  function t(key, params) {
    const table = STRINGS[lang] || STRINGS.ru;
    let str = table[key] != null ? table[key] : key;
    if (params) {
      for (const k of Object.keys(params)) {
        str = str.replace(`{${k}}`, params[k]);
      }
    }
    return str;
  }

  function getLang() { return lang; }

  function setLang(next) {
    if (next !== "ru" && next !== "uz") return;
    lang = next;
    localStorage.setItem("lang", lang);
  }

  // Pick the label for the active language from an option/row carrying
  // both label_ru and label_uz.
  function label(obj) {
    if (!obj) return "";
    return (lang === "uz" ? obj.label_uz : obj.label_ru) || obj.label_ru || "";
  }

  window.i18n = { t, getLang, setLang, label };
})();
