<?php
/**
 * Add Gujarati (and Hindi) language support to temple single pages.
 *
 * The Elementor template only has mr_lang / en_lang / hi_lang divs.
 * This hook injects gu_lang content + patches the language selector.
 *
 * Add this to: wp-content/themes/hello-theme-child/functions.php
 */
add_action( 'wp_footer', function () {
    if ( ! is_singular( 'temple' ) ) {
        return;
    }

    $post_id = get_the_ID();

    // Languages to inject: switcher_code => [acf_field, dropdown_label]
    // NOTE: site uses 'gj' (not 'gu') as the Gujarati switcher code → class gj_lang
    $inject = [
        'gj' => [ 'gujarati_content', 'ગુજરાતી' ],
        'hi' => [ 'hi_translation',   'हिन्दी'  ],
    ];

    $has_content = [];
    foreach ( $inject as $code => [ $field, $label ] ) {
        $content = get_field( $field, $post_id );
        if ( empty( trim( strip_tags( $content ) ) ) ) {
            continue;
        }
        $has_content[ $code ] = [ 'content' => $content, 'label' => $label ];
        // Output hidden content div — JS will show it when user picks this lang.
        echo '<div class="' . esc_attr( $code ) . '_lang dis_lang pilgrim-extra-lang" style="display:none;padding:20px 40px;">';
        echo $content;   // already sanitized by ACF
        echo '</div>';
    }

    if ( empty( $has_content ) ) {
        return;
    }

    // Build the JS options list
    $options_js = '';
    foreach ( $has_content as $code => $info ) {
        $options_js .= sprintf(
            'if(!$("#language-select option[value=\'%s\']").length){$("#language-select").append(\'<option value="%s">%s</option>\');}',
            esc_js( $code ),
            esc_js( $code ),
            esc_js( $info['label'] )
        );
    }

    ?>
    <style>
        .pilgrim-extra-lang { max-width: 1140px; margin: 0 auto; }
    </style>
    <script>
    jQuery(document).ready(function ($) {
        // 1. Add dropdown options for injected languages
        <?php echo $options_js; ?>

        // 2. Extend language switching to cover injected lang classes
        var extraLangs = <?php echo json_encode( array_keys( $has_content ) ); ?>;

        $('#language-select').on('change', function () {
            var selected = $(this).val();
            $.each(extraLangs, function (_, code) {
                var $els = $('.' + code + '_lang');
                if (code === selected) {
                    $els.removeClass('dis_lang').show();
                } else {
                    $els.addClass('dis_lang').hide();
                }
            });
        });

        // 3. If Gujarati (or another extra lang) was somehow pre-selected, show it.
        var current = $('#language-select').val();
        if (extraLangs.indexOf(current) !== -1) {
            $('.' + current + '_lang').removeClass('dis_lang').show();
        }
    });
    </script>
    <?php
}, 99 );
