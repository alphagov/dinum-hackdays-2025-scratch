function changeContentPaneByFragment(defaultFragment) {
    var hash = window.location.hash;
    if (hash === '') {
        hash = defaultFragment;
    } else {
        hash = hash.replace('#', '');
    }

    document.querySelectorAll('.main-content').forEach(function (pane) {
        if (pane.id.indexOf(hash) !== -1) {
            pane.classList.remove('hidden');
        } else {
            pane.classList.add('hidden');
        }
    });
}

const ulFragmentLinks = document.getElementsByClassName("ul-fragment-links");

if (ulFragmentLinks.length > 0) {
    const defaultFragment = document.getElementById("main-content-members") ? "members" : "about";
    window.addEventListener('hashchange', function () {
        changeContentPaneByFragment(defaultFragment)
    });
    changeContentPaneByFragment(defaultFragment);
}

function disable_button(button) {
    button.disabled = true;
    button.classList.add("disabled");
    // continue to submit the form
    button.form.submit();
}
