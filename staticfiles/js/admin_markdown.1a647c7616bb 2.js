document.addEventListener('DOMContentLoaded', function() {
    var contentAreas = document.querySelectorAll('textarea[name="content"], .field-content textarea');
    contentAreas.forEach(function(area) {
        new EasyMDE({ 
            element: area,
            spellChecker: false,
            autosave: {
                enabled: true,
                uniqueId: area.id || "admin_markdown",
                delay: 1000,
            },
            status: ["autosave", "lines", "words", "cursor"],
            placeholder: "Markdown format ဖြင့် စာသားများ ရေးသားနိုင်ပါသည်။...",
            forceSync: true,
            toolbar: [
                "bold", "italic", "heading", "|",
                "quote", "unordered-list", "ordered-list", "|",
                "link", "image", "table", "|",
                "preview", "side-by-side", "fullscreen", "|",
                "guide"
            ]
        });
    });
});

