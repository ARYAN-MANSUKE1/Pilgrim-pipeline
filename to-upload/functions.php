<?php
/**
 * Theme functions and definitions.
 *
 * For additional information on potential customization options,
 * read the developers' documentation:
 *
 * https://developers.elementor.com/docs/hello-elementor-theme/
 *
 * @package HelloElementorChild
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

define( 'HELLO_ELEMENTOR_CHILD_VERSION', '2.0.0' );

/**
 * Load child theme scripts & styles.
 *
 * @return void
 */
function hello_elementor_child_scripts_styles() {
	wp_enqueue_style(
		'hello-elementor-child-style',
		get_stylesheet_directory_uri() . '/style.css',
		[
			'hello-elementor-theme-style',
		],
		HELLO_ELEMENTOR_CHILD_VERSION
	);
}
add_action( 'wp_enqueue_scripts', 'hello_elementor_child_scripts_styles', 20 );

// ================================= Custom Code ================================= //

// ================================= Search Bar ================================== //
function custom_post_type_search_form() {
    ob_start(); ?>
    <form role="search" method="get" class="search-form" action="<?php echo home_url( '/' ); ?>">
		<input type="search" class="search-field" placeholder="<?php echo esc_attr_x( 'Search Temple', 'placeholder' ) ?>" value="" name="s" title="<?php echo esc_attr_x( 'Search for:', 'label' ) ?>" />
        <?php $select_city = array('taxonomy' => 'city', 'value_field' => 'slug', 'name' => 'city', 'show_option_none' => __( 'Select City' ),'option_none_value' => '0', 'orderby' => 'parent', 'order' => 'ASC', 'hierarchical'  =>1, 'hide_empty' => 0); ?>
        <?php wp_dropdown_categories($select_city); ?>
        <input type="hidden" name="post_type" value="temple" />
    	<button type="submit" id="searchsubmit" value="Search">SEARCH</button>
    </form>
    <?php return ob_get_clean();
}
add_shortcode('search_bar', 'custom_post_type_search_form');

// Temple Short Code
// ============================================================ Property Custom Post type Stort Code Start

// property Custom Post type End Code Start 
function custom_post_type_shortcode($atts) {
    ob_start();
    // Extract shortcode attributes
    $atts = shortcode_atts(
        array(
            'posts_per_page' => 6,
            'paged'          => get_query_var('paged') ? get_query_var('paged') : 1,
        ),
        $atts,
        'custom_post_type'
    );
    // Custom query
    $query_args = array(
        'post_type'      => 'temple', // Replace with your custom post type slug
        'posts_per_page' => $atts['posts_per_page'],
        'paged'          => $atts['paged'],
    );
    $custom_query = new WP_Query($query_args);
    // Display the loop
    ?>
	<div>
		<?php if ($custom_query->have_posts()) : ?>
			<div class="temple-grid-format">
				<?php while ($custom_query->have_posts()) : $custom_query->the_post(); ?>
				<div class="temple-block">
					<div class="temple-data">
						<?php echo '<a href="'.get_permalink().'">' ?>
							<div class="post-feature-image" style="background-image: url('<?php echo get_the_post_thumbnail_url(); ?>');"></div>
<!-- 							< ?php echo get_the_post_thumbnail(); ?> -->
										<div class="mr_lang dis_lang" style="display: block;">
											<h5><?php echo esc_html( get_field('marathi_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> अधिक माहिती </span>'; ?>
										</div>
										<div class="en_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('english_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> View Details </span>'; ?>
										</div>
										<div class="hi_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('hindi_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> विवरण देखें </span>'; ?>
										</div>
										<div class="gj_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('gujarati_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> વધુ માહિતી </span>'; ?>
										</div>
										<div class="ta_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('tamil_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> மேலும் விவரங்கள் </span>'; ?>
										</div>
										<div class="te_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('telugu_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> మరిన్ని వివరాలు </span>'; ?>
										</div>
										<div class="ml_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('malayalam_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> കൂടുതൽ വിവരങ്ങൾ </span>'; ?>
										</div>
										<div class="kn_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('kannada_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> ಹೆಚ್ಚಿನ ಮಾಹಿತಿ </span>'; ?>
										</div>
										<div class="bn_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('bengali_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> আরও তথ্য </span>'; ?>
										</div>
										<div class="pa_lang dis_lang" style="display: none;">
											<h5><?php echo esc_html( get_field('punjabi_title') ?: get_the_title() ); ?></h5>
											<?php echo '<span class="view-details-btn"> ਹੋਰ ਜਾਣਕਾਰੀ </span>'; ?>
										</div>
							<?php echo the_excerpt(); ?>
						<?php echo '</a>'; ?>
					</div>
				</div>
			<?php endwhile; ?>
			</div>
				<?php
			else :
				echo 'No Temples Found';
			endif;
		?>
	</div>
	<?php
    wp_reset_postdata();
    return ob_get_clean();
}
add_shortcode('temple_grid', 'custom_post_type_shortcode');

// ============================================================ Gallery Slider Shortode

function ls_scripts_styles() {
	wp_enqueue_style( 'lightslidercss', get_stylesheet_directory_uri(). '/property-assets/css/lightslider.css' , array(), '1.0.0', 'all' );
	wp_enqueue_script( 'lightsliderjs', get_stylesheet_directory_uri() . '/property-assets/js/lightslider.js', array( 'jquery' ), '1.0.0', true );
	wp_enqueue_script( 'lightsliderinit', get_stylesheet_directory_uri() . '/property-assets/js/lightslider-init.js', array( 'lightsliderjs' ), '1.0.0', true );
}
add_action( 'wp_enqueue_scripts', 'ls_scripts_styles', 20 );
function enqueue_fancybox_assets() {
    wp_enqueue_style('fancybox-css', 'https://cdnjs.cloudflare.com/ajax/libs/fancybox/3.5.7/jquery.fancybox.min.css');
    wp_enqueue_script('fancybox-js', 'https://cdnjs.cloudflare.com/ajax/libs/fancybox/3.5.7/jquery.fancybox.min.js', array('jquery'), null, true);
}
add_action('wp_enqueue_scripts', 'enqueue_fancybox_assets');

function initialize_fancybox() {
    ?>
    <script type="text/javascript">
        jQuery(document).ready(function($) {
            $('[data-fancybox="gallery"]').fancybox({
                // Options for customization
            });
        });
    </script>
    <?php
}
add_action('wp_footer', 'initialize_fancybox');

// Where you want the slider add the shortcode [lightslider_looper]	
function tl_light_looper()  {
    $images = get_field('gallery');
	ob_start();
	if( $images ): 
	 ?>
		<div class="tl_slide_photo_container">
			<ul id="light-slider" class="image-gallery">
				<?php foreach( $images as $image ): ?>
				<li data-thumb="<?php echo $image['url']; ?>" >
					<a href="<?php echo esc_url($image['url']); ?>" data-fancybox="gallery" data-caption="<?php echo esc_attr($image['alt']); ?>">
						<img src="<?php echo $image['url']; ?>" alt="<?php echo $image['alt']; ?>" />
					</a>
				</li>
				<?php endforeach; ?>
		 	</ul>
		</div>
	<?php endif; 
	return ob_get_clean();
}
add_shortcode( 'lightslider_looper', 'tl_light_looper' );

// ============================================================ Excerpt Length
function mytheme_custom_excerpt_length( $length ) {
    return 15;
}
add_filter( 'excerpt_length', 'mytheme_custom_excerpt_length', 999 );

// ============================================================ Allow SVG File Format
add_filter( 'wp_check_filetype_and_ext', function($data, $file, $filename, $mimes) {
  global $wp_version;
  if ( $wp_version !== '4.7.1' ) {
     return $data;
  }
  $filetype = wp_check_filetype( $filename, $mimes );
  return [
      'ext'             => $filetype['ext'],
      'type'            => $filetype['type'],
      'proper_filename' => $data['proper_filename']
  ];
}, 10, 4 );

function cc_mime_types( $mimes ){
  $mimes['svg'] = 'image/svg+xml';
  return $mimes;
}
add_filter( 'upload_mimes', 'cc_mime_types' );

// ============================================================ Language Swatch

add_action( 'wp_footer', 'mycustom_wp_footer' );
function mycustom_wp_footer() { ?>
    <script>
	// Function to set cookie
        function setCookie(name, value, days) {
            var expires = "";
            if (days) {
                var date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                expires = "; expires=" + date.toUTCString();
            }
            document.cookie = name + "=" + (value || "") + expires + "; path=/";
        }
        // Function to get cookie value
        function getCookie(name) {
            var nameEQ = name + "=";
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {
                var c = ca[i];
                while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
            }
            return null;
        }
        // Function to delete cookie
        function eraseCookie(name) {
            document.cookie = name + '=; Max-Age=-99999999;';
        }
        document.addEventListener("DOMContentLoaded", function () {
            // Check if language preference cookie exists
            var language = getCookie("language");
            if (language) {
                document.getElementById("language-select").value = language;
                toggleLanguage(language);
            }
        });
        // Function to toggle language
        function toggleLanguage(selectedLanguage) {
            // Show elements based on selected language
            var elements = document.querySelectorAll(".dis_lang");
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = elements[i].classList.contains(selectedLanguage + "_lang") ? "block" : "none";
            }
            // Set cookie for selected language
            setCookie("language", selectedLanguage, 30);
        }
        document.getElementById("language-select").addEventListener("change", function () {
            var selectedLanguage = this.value;
            toggleLanguage(selectedLanguage);
        });
		
		$(document).ready(function(){
			$(".share-btn").click(function(){
				$(".share-links").toggle(); // Show/hide share links
			});
		});
    </script>
<?php }

// ============================================================ 
function get_related_custom_posts_by_taxonomy($post_id, $taxonomy, $number_of_posts = 3) {
    $terms = wp_get_post_terms($post_id, $taxonomy);
    if ($terms) {
        $term_ids = array();
        foreach ($terms as $term) {
            $term_ids[] = $term->term_id;
        }
        $args = array(
            'post_type' => get_post_type($post_id),
            'post__not_in' => array($post_id),
            'posts_per_page' => $number_of_posts,
            'tax_query' => array(
                array(
                    'taxonomy' => $taxonomy,
                    'field'    => 'term_id',
                    'terms'    => $term_ids,
                ),
            ),
            'ignore_sticky_posts' => 1
        );        
        $related_posts = new WP_Query($args);
        return $related_posts;
    }
    return false;
}

// ============================================================ Search Page Pagination 
function search_filter($query) {
  if ( !is_admin() && $query->is_main_query() ) {
    if ($query->is_search) {
      $query->set('paged', ( get_query_var('paged') ) ? get_query_var('paged') : 1 );
      $query->set('posts_per_page',6);
    }
  }
}
// ====================================================================================
// Glossary Code
// function create_glossary_post_type() {
//     register_post_type('glossary',
//         array(
//             'labels' => array(
//                 'name' => __('Glossary'),
//                 'singular_name' => __('Glossary Term')
//             ),
//             'public' => true,
//             'has_archive' => true,
//             'rewrite' => array('slug' => 'glossary'),
//             'supports' => array('title', 'editor'),
//         )
//     );
// }
// add_action('init', 'create_glossary_post_type');

// =============================== Glossary with ACF Start =============================== //
// Fetch glossary terms for temple posts
// function fetch_glossary_terms_for_temple($content) {
//     if (is_singular('temple')) {
//         $glossary_terms = get_field('glossary_terms'); // ACF field where primary glossary terms are linked
//         $glossary_terms_secondary = get_field('glossary_terms_secondary'); // ACF field where secondary glossary terms are linked

//         Debug: Log the glossary terms
//         error_log('Primary Glossary Terms: ' . print_r($glossary_terms, true));
//         error_log('Secondary Glossary Terms: ' . print_r($glossary_terms_secondary, true));

//         Function to process glossary terms
//         function process_glossary_terms($terms, $content) {
//             if ($terms) {
//                 foreach ($terms as $term) {
//                     $term_title = get_the_title($term->ID);
//                     $term_definition = get_post_field('post_content', $term->ID);

//                     if (!empty($term_definition)) {
//                         $tooltip = '<span class="tooltips" title="' . esc_attr($term_definition) . '">' . $term_title . '</span>';
//                         $content = str_replace($term_title, $tooltip, $content);
//                     }
//                 }
//             }
//             return $content;
//         }

//         Process primary glossary terms
//         $content = process_glossary_terms($glossary_terms, $content);

//         Process secondary glossary terms
//         $content = process_glossary_terms($glossary_terms_secondary, $content);
//     }

//     return $content;
// }
// add_filter('mr_translation', 'fetch_glossary_terms_for_temple');
// add_filter('er_translation', 'fetch_glossary_terms_for_temple');
// =============================== Glossary with ACF End =============================== //

// function fetch_glossary_terms_for_temple($content) {
//     if (is_singular('temple')) {
//         $glossary_terms = get_field('glossary_terms'); // Fetch glossary terms linked to the temple post

//         if ($glossary_terms) {
//             foreach ($glossary_terms as $term) {
//                 $term_title = get_the_title($term->ID);
// //                 $en_translation = get_field('en_translation', $term->ID); // Fetch the English translation using ACF
// 				$term_definition = get_post_field('post_content', $term->ID);

//                 if (!empty($term_definition)) {
//                     $tooltip = '<span class="tooltips" title="' . esc_attr($term_definition) . '">' . $term_title . '</span>';
//                     $content = str_replace($term_title, $tooltip, $content);
//                 }
//             }
//         }
//     }
//     return $content;
// }
// add_filter('en_translation', 'fetch_glossary_terms_for_temple'); // Use ACF filter for WYSIWYG content

// Add CSS for tooltip styling
// function add_tooltip_css() {
//     echo '
//     <style>
//         .tooltips { position: relative; cursor: pointer; border-bottom: 1px dotted #000; }
// 		.tooltips:hover::after { content: none; }
// 		@media only screen and (max-width: 600px) {
// 			.tooltips:hover::after { content: attr(title); position: absolute; bottom: 100%; background-color: #333; color: #fff; padding: 5px; border-radius: 3px; display: flex; flex-wrap: wrap !important; font-size: 14px; font-weight: 500; min-width: 250px !important; text-align: left; }
// 		}
//     </style>
//     ';
// }
// add_action('wp_head', 'add_tooltip_css');

// Taxonomy in Temple List
function add_custom_taxonomy_to_list_table($columns) {
    $columns['temple-category'] = __('Temple Category'); // Change 'product_category' to your taxonomy name
    return $columns;
}
add_filter('manage_edit-temple_columns', 'add_custom_taxonomy_to_list_table'); // Replace 'product' with your post type

function display_custom_taxonomy_column($column, $post_id) {
    if ($column === 'temple-category') {
        $terms = get_the_terms($post_id, 'temple-category'); // Replace 'product_category' with your taxonomy name
        if (!empty($terms)) {
            $term_names = wp_list_pluck($terms, 'name');
            echo esc_html(implode(', ', $term_names));
        } else {
            echo __('-');
        }
    }
}

add_action('manage_temple_posts_custom_column', 'display_custom_taxonomy_column', 10, 2);



// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //

// Enqueue script (child-theme aware) and pass AJAX URL + nonce
function load_custom_scripts() {
    $script_path = '/js/temple-filter.js';
    // Use filemtime for cache-busting in development
    $version = file_exists(get_stylesheet_directory() . $script_path) ? filemtime(get_stylesheet_directory() . $script_path) : false;

    wp_enqueue_script(
        'temple-filter',
        get_stylesheet_directory_uri() . $script_path,
        array('jquery'),
        $version,
        true
    );

    wp_localize_script('temple-filter', 'templeFilter', array(
        'ajax_url' => admin_url('admin-ajax.php'),
        'nonce'    => wp_create_nonce('temple-filter-nonce'),
    ));
}
add_action('wp_enqueue_scripts', 'load_custom_scripts');


// Shortcode: search form for Temple CPT
function temple_search_filter_shortcode() {
    ob_start();
    ?>
    <form id="temple-filter-form" class="search-form" method="GET" action="<?php echo esc_url( home_url('/') ); ?>">
        <select id="parent-city" name="parent_city">
            <option value="">Select State</option>
            <?php
            $parent_terms = get_terms(array(
                'taxonomy'   => 'city',
                'parent'     => 0,
                'hide_empty' => false,
            ));
            if (!is_wp_error($parent_terms)) {
                foreach ($parent_terms as $term) {
                    echo '<option value="' . esc_attr($term->slug) . '">' . esc_html($term->name) . '</option>';
                }
            }
            ?>
        </select>

        <select name="city" id="child-city">
            <option value="">Select District</option>
        </select>

        <input class="search-field" type="text" name="s" placeholder="Temples Name" value="<?php echo esc_attr( get_search_query() ); ?>" />

        <input type="hidden" name="post_type" value="temple" />
        <button type="submit" id="searchsubmit" value="Search">SEARCH</button>
    </form>
    <?php
    return ob_get_clean();
}
add_shortcode('temple_search_filter', 'temple_search_filter_shortcode');


// AJAX handlers for getting child terms
add_action('wp_ajax_get_child_terms', 'get_child_terms');
add_action('wp_ajax_nopriv_get_child_terms', 'get_child_terms');

function get_child_terms() {
    // Verify nonce
    check_ajax_referer('temple-filter-nonce', 'nonce');

    $parent_slug = isset($_POST['parent_slug']) ? sanitize_text_field( wp_unslash( $_POST['parent_slug'] ) ) : '';

    if (empty($parent_slug)) {
        wp_send_json_error( array( 'message' => 'No parent provided' ) );
    }

    $parent_term = get_term_by('slug', $parent_slug, 'city');

    if (!$parent_term || is_wp_error($parent_term)) {
        wp_send_json_error( array( 'message' => 'Parent term not found' ) );
    }

    $child_terms = get_terms(array(
        'taxonomy'   => 'city',
        'parent'     => $parent_term->term_id,
        'hide_empty' => false,
    ));

    $options = '<option value="">Select District</option>';
    if (!is_wp_error($child_terms) && !empty($child_terms)) {
        foreach ($child_terms as $term) {
            $options .= '<option value="' . esc_attr($term->slug) . '">' . esc_html($term->name) . '</option>';
        }
    }

    wp_send_json_success( array( 'options' => $options ) );
}


// Make the search/search results respect the "city" GET parameter for "temple" CPT
function temple_city_search_query( $query ) {
    // Only affect frontend main query
    if ( is_admin() || ! $query->is_main_query() ) {
        return;
    }

    // We want to affect:
    // - front-end searches where post_type=temple
    // - or when post_type is not set but we want to catch temple listing pages if you need that adjust accordingly
    $request_post_type = isset( $_GET['post_type'] ) ? sanitize_text_field( wp_unslash( $_GET['post_type'] ) ) : '';
    $is_temple_search = ( $request_post_type === 'temple' ) || ( $query->get('post_type') === 'temple' );

    if ( ! $is_temple_search ) {
        return;
    }

    // If a city slug is present in GET params, convert it to tax_query
    if ( isset( $_GET['city'] ) && ! empty( $_GET['city'] ) ) {
        $city_slug = sanitize_text_field( wp_unslash( $_GET['city'] ) );
        $term = get_term_by( 'slug', $city_slug, 'city' );

        if ( $term && ! is_wp_error( $term ) ) {
            // Gather this term and any descendant terms (so parent selection includes children)
            $term_ids = array( (int) $term->term_id );

            // get descendants
            $descendants = get_terms( array(
                'taxonomy'   => 'city',
                'hide_empty' => false,
                'child_of'   => $term->term_id,
                'fields'     => 'ids',
            ) );
            if ( ! is_wp_error( $descendants ) && ! empty( $descendants ) ) {
                $term_ids = array_merge( $term_ids, $descendants );
            }

            // Build the tax_query to filter temple CPT by city term ids
            $tax_query = array(
                array(
                    'taxonomy' => 'city',
                    'field'    => 'term_id',
                    'terms'    => array_map( 'intval', $term_ids ),
                    'include_children' => false,
                    'operator' => 'IN',
                ),
            );

            $query->set( 'tax_query', $tax_query );
        }
    }
}
add_action( 'pre_get_posts', 'temple_city_search_query' );

// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // //
add_action('pre_get_posts', 'filter_temples_by_city');
function filter_temples_by_city($query) {
    if (!is_admin() && $query->is_main_query() && is_search() && isset($_GET['city']) && !empty($_GET['city'])) {
        $query->set('post_type', 'temple');
        $query->set('tax_query', array(array(
            'taxonomy' => 'city',
            'field'    => 'slug',
            'terms'    => sanitize_text_field($_GET['city']),
        )));
    }
}

//////////////////////////////////////////////////////////////////////////////////////

function temple_marquee_slider_shortcode() {
    ob_start();

    $temple_query = new WP_Query(array(
        'post_type'      => 'temple',
        'posts_per_page' => 30,
        'post_status'    => 'publish',
    ));

    if ($temple_query->have_posts()) :
        ?>
        <style>
        .temple-marquee-wrapper { overflow: hidden; position: relative; width: 100%; background: #e4965030; padding: 15px 0px; }
        .temple-marquee-track { display: flex; width: max-content; animation: marqueeScroll 60s linear infinite; }
        .temple-marquee-item { flex: 0 0 auto; width: 200px; margin-right: 15px; text-align: center; }
/*         .temple-marquee-item img { max-height: 100%; width: auto; display: block; margin: 0 auto 5px; object-fit: contain; } */
		.slider-post-feature-image { width: 100%; height: 125px; background-position: center; background-size: cover; background-repeat: no-repeat; margin-bottom: 7px; }
        .temple-marquee-item h4 { font-size: 12px; color: #333; margin: 0; }
		.temple-marquee-item a { text-decoration: none; color: inherit; }
		.temple-marquee-item a h4 { text-decoration: none; }

        @keyframes marqueeScroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-15%); }
        }
        .temple-marquee-wrapper:hover .temple-marquee-track { animation-play-state: paused; }
        @media (max-width: 600px) {
            .temple-marquee-item { width: 150px; }
			.slider-post-feature-image { height: 100px; }
        }
        </style>

        <div class="temple-marquee-wrapper">
            <div class="temple-marquee-track">
                <?php
                // Output items twice to fake infinite loop
                for ($i = 0; $i < 2; $i++) :
                    $temple_query->rewind_posts();
                    while ($temple_query->have_posts()) : $temple_query->the_post();
                        $image = get_the_post_thumbnail_url(get_the_ID(), 'medium');
//                         $title = ( function_exists('pll_current_language') && pll_current_language() === 'en' ) 
//     ? get_field('en_translation') 
//     : get_field('marathi_title');
                        $link  = get_permalink();
                        ?>
                        <div class="temple-marquee-item">
                            <a href="<?php echo esc_url($link); ?>" target="_blank">
                                <?php if ($image): ?>
                                    <div class="slider-post-feature-image" style="background-image: url('<?php echo get_the_post_thumbnail_url(); ?>');"></div>
<!-- 									<img src="< ?php echo esc_url($image); ?>" alt="< ?php echo esc_attr($title); ?>" /> -->
                                <?php endif; ?>
                                <div class="mr_lang dis_lang" style="display: block;">
									<h4><?php the_field('marathi_title'); ?></h4>
								</div>
								<div class="en_lang dis_lang" style="display: none;">
									<h4><?php echo esc_html(get_the_title()); ?></h4>
								</div>
								<div class="hi_lang dis_lang" style="display: none;">
									<h4><?php the_field('hindi_title'); ?></h4>
								</div>
                            </a>
                        </div>
                    <?php endwhile;
                endfor;
                wp_reset_postdata();
                ?>
            </div>
        </div>
        <?php
    endif;
    return ob_get_clean();
}
add_shortcode('temple_slider', 'temple_marquee_slider_shortcode');

// CPT City Taxonomy Dropdown in Dashboard
add_action('restrict_manage_posts', function ($post_type) {

    if ($post_type !== 'temple') {
        return;
    }

    $taxonomy = 'city';

    $selected = $_GET[$taxonomy] ?? '';
    $tax_obj  = get_taxonomy($taxonomy);

    if (!$tax_obj) {
        return;
    }

    wp_dropdown_categories([
        'show_option_all' => __('All ' . $tax_obj->label),
        'taxonomy'        => $taxonomy,
        'name'            => $taxonomy,
        'orderby'         => 'name',
        'selected'        => $selected,
        'hierarchical'    => true,
        'depth'           => 3,
        'show_count'      => false,
        'hide_empty'      => false,
    ]);
});
add_filter('parse_query', function ($query) {

    global $pagenow;

    if (
        $pagenow === 'edit.php' &&
        isset($_GET['post_type']) &&
        $_GET['post_type'] === 'temple' &&
        !empty($_GET['city']) &&
        is_numeric($_GET['city'])
    ) {
        $term = get_term_by('id', $_GET['city'], 'city');
        if ($term) {
            $query->query_vars['city'] = $term->slug;
        }
    }
});


/* ==========================================================================
   PILGRIM MULTILINGUAL -- added for the translation + audio pipeline.
   Everything above this banner is live's original functions.php, unchanged.
   Rollback: delete everything below this banner.
   ========================================================================== */

add_action( 'acf/init', 'pilgrim_rest_language_fields' );
function pilgrim_rest_language_fields() {
    if ( ! function_exists( 'acf_add_local_field_group' ) ) { return; }
    $fields = array(
        array( 'key' => 'field_pilgrimrest_marathi_audio', 'name' => 'marathi_audio',
               'label' => 'Marathi Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_english_title', 'name' => 'english_title',
               'label' => 'English Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_english_audio', 'name' => 'english_audio',
               'label' => 'English Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_hindi_audio', 'name' => 'hindi_audio',
               'label' => 'Hindi Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_gujarati_content', 'name' => 'gujarati_content',
               'label' => 'Gujarati Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_gujarati_title', 'name' => 'gujarati_title',
               'label' => 'Gujarati Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_gujarati_audio', 'name' => 'gujarati_audio',
               'label' => 'Gujarati Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_tamil_content', 'name' => 'tamil_content',
               'label' => 'Tamil Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_tamil_title', 'name' => 'tamil_title',
               'label' => 'Tamil Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_tamil_audio', 'name' => 'tamil_audio',
               'label' => 'Tamil Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_telugu_content', 'name' => 'telugu_content',
               'label' => 'Telugu Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_telugu_title', 'name' => 'telugu_title',
               'label' => 'Telugu Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_telugu_audio', 'name' => 'telugu_audio',
               'label' => 'Telugu Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_malayalam_content', 'name' => 'malayalam_content',
               'label' => 'Malayalam Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_malayalam_title', 'name' => 'malayalam_title',
               'label' => 'Malayalam Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_malayalam_audio', 'name' => 'malayalam_audio',
               'label' => 'Malayalam Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_kannada_content', 'name' => 'kannada_content',
               'label' => 'Kannada Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_kannada_title', 'name' => 'kannada_title',
               'label' => 'Kannada Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_kannada_audio', 'name' => 'kannada_audio',
               'label' => 'Kannada Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_bengali_content', 'name' => 'bengali_content',
               'label' => 'Bengali Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_bengali_title', 'name' => 'bengali_title',
               'label' => 'Bengali Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_bengali_audio', 'name' => 'bengali_audio',
               'label' => 'Bengali Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_punjabi_content', 'name' => 'punjabi_content',
               'label' => 'Punjabi Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_punjabi_title', 'name' => 'punjabi_title',
               'label' => 'Punjabi Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_punjabi_audio', 'name' => 'punjabi_audio',
               'label' => 'Punjabi Audio', 'type' => 'file', 'return_format' => 'array', ),
    );
    acf_add_local_field_group( array(
        'key' => 'group_pilgrim_rest_languages',
        'title' => 'Temple Fields (pipeline languages)',
        'fields' => $fields,
        'location' => array( array( array(
            'param' => 'post_type', 'operator' => '==', 'value' => 'temple',
        ) ) ),
        'show_in_rest' => 1,
    ) );
}

function pilgrim_default_languages() {
    // code => [English name, native self-name shown in the dropdown]
    $known = array(
        'mr' => array( 'Marathi', 'मराठी' ),   'en' => array( 'English', 'English' ),
        'hi' => array( 'Hindi', 'हिन्दी' ),     'gj' => array( 'Gujarati', 'ગુજરાતી' ),
        'ta' => array( 'Tamil', 'தமிழ்' ),      'te' => array( 'Telugu', 'తెలుగు' ),
        'ml' => array( 'Malayalam', 'മലയാളം' ), 'kn' => array( 'Kannada', 'ಕನ್ನಡ' ),
        'bn' => array( 'Bengali', 'বাংলা' ),    'pa' => array( 'Punjabi', 'ਪੰਜਾਬੀ' ),
    );
    $out = array();
    foreach ( $known as $code => $pair ) {
        $out[ $code ] = array(
            'name' => $pair[0], 'native' => $pair[1],
            'fields' => false, 'chrome' => true, 'visible' => true,
        );
    }
    return $out;
}

function pilgrim_get_languages() {
    $langs = get_option( 'pilgrim_languages', null );
    if ( ! is_array( $langs ) || empty( $langs ) ) {
        $langs = pilgrim_default_languages();
        update_option( 'pilgrim_languages', $langs, false );
    }
    return $langs;
}

function pilgrim_audio_url( $field ) {
    $v = get_field( $field );
    if ( empty( $v ) ) {
        return '';
    }
    if ( is_array( $v ) ) {
        return esc_url( isset( $v['url'] ) ? $v['url'] : '' );
    }
    if ( is_numeric( $v ) ) {
        return esc_url( (string) wp_get_attachment_url( (int) $v ) );
    }
    return esc_url( (string) $v );
}

function pilgrim_extend_language_and_audio() {

    $audio_mr = '';
    $audio_en = '';
    $audio_hi = '';
    $audio_gj = '';
    $audio_ta = '';
    $audio_te = '';
    $audio_ml = '';
    $audio_kn = '';
    $audio_bn = '';
    $audio_pa = '';

    if ( is_singular('temple') ) {
        $audio_mr = pilgrim_audio_url('marathi_audio');
        $audio_en = pilgrim_audio_url('english_audio');
        $audio_hi = pilgrim_audio_url('hindi_audio');
        $audio_gj = pilgrim_audio_url('gujarati_audio');
        $audio_ta = pilgrim_audio_url('tamil_audio');
        $audio_te = pilgrim_audio_url('telugu_audio');
        $audio_ml = pilgrim_audio_url('malayalam_audio');
        $audio_kn = pilgrim_audio_url('kannada_audio');
        $audio_bn = pilgrim_audio_url('bengali_audio');
        $audio_pa = pilgrim_audio_url('punjabi_audio');
    }

    $audio_json = json_encode( array(
        'mr' => $audio_mr,
        'en' => $audio_en,
        'hi' => $audio_hi,
        'gj' => $audio_gj,
        'ta' => $audio_ta,
        'te' => $audio_te,
        'ml' => $audio_ml,
        'kn' => $audio_kn,
        'bn' => $audio_bn,
        'pa' => $audio_pa,
    ));
    $is_temple = is_singular('temple') ? 'true' : 'false';

    // Cached chrome-string dictionary (survives independently of Elementor/migrations).
    $ui_i18n = get_option( 'pilgrim_ui_i18n', array() );
    if ( ! is_array( $ui_i18n ) ) {
        $ui_i18n = array();
    }
    $ui_i18n_json = wp_json_encode( $ui_i18n );

    // Language registry -- drives which dropdown options appear (visible=true only).
    $langs_json = wp_json_encode( pilgrim_get_languages() );
    ?>

    <style>
    #pilgrim-audio-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.55);
        background: transparent;
        color: #ffffff;
        font-size: 15px;
        cursor: pointer;
        margin-left: 6px;
        vertical-align: middle;
        transition: background 0.18s, border-color 0.18s;
        padding: 0;
        line-height: 1;
        flex-shrink: 0;
    }
    #pilgrim-audio-btn:hover { background: rgba(255,255,255,0.18); border-color: #ffffff; }
    #pilgrim-audio-btn.playing { background: #FB8B24; border-color: #FB8B24; }
    #pilgrim-audio-btn.hidden { display: none !important; }
    #lang-audio-wrap { display: inline-flex; align-items: center; gap: 6px; }
    </style>

    <audio id="pilgrim-global-audio" preload="none" style="display:none;">
        <source id="pilgrim-audio-src" src="" type="audio/mpeg">
    </audio>

    <script>
    (function () {
        var AUDIO     = <?php echo $audio_json; ?>;
        var IS_TEMPLE = <?php echo $is_temple; ?>;
        var UI_I18N   = <?php echo $ui_i18n_json; ?>;   // { lang: { key: text } }, from wp_options
        var LANGS     = <?php echo $langs_json; ?>;     // { code: {name, native, fields, chrome, visible} }

        // Hardcoded English fallback: guarantees no chrome string is ever blank,
        // even before a language is translated or if the option is empty.
        var UI_FALLBACK_EN = {
            nav_home:"Home", nav_about:"About Us", nav_temples:"Temples",
            nav_state:"State", nav_sponsors:"Sponsors", nav_contact:"Contact Us",
            nav_privacy:"Privacy Policy", nav_terms:"Terms & Conditions",
            s_instagram:"Instagram", s_facebook:"Facebook", s_youtube:"YouTube",
            copyright:"All Rights Reserved."
        };

        function applyUiI18n(lang) {
            var dict = UI_I18N[lang] || {};
            var en   = UI_I18N['en'] || {};
            document.querySelectorAll('[data-i18n]').forEach(function (el) {
                var key = el.getAttribute('data-i18n');
                var text = dict[key] || en[key] || UI_FALLBACK_EN[key];
                if (text) el.textContent = text;
            });
        }

        // Keep the nav menu on ONE line, beside the logo, no matter how long a
        // language's labels run -- and no matter what language gets added
        // later.
        //
        // Verified against the theme's actual header markup: the flex row
        // that wraps is  .site-branding (logo)  vs  .main-header-extra-class
        // (which contains the nav, the language dropdown, AND the mobile
        // hamburger toggle) -- both siblings under .header-inner. The nav
        // itself is nested INSIDE .main-header-extra-class, not a sibling of
        // the logo, so comparing the nav's own position to its previous
        // sibling (an earlier attempt) never worked -- there wasn't one.
        //
        // Fix: detect wrap by comparing .main-header-extra-class's top to
        // .site-branding's bottom. If it's no longer on the same row, shrink
        // both the nav's font-size AND each link's horizontal padding (there's
        // more competing for space in that row than just the nav -- the
        // language dropdown and hamburger toggle too, so font alone may not
        // be enough). Resets both to default first each run so English (or
        // any short language) grows back to full size.
        function fitNavToOneLine() {
            var nav = document.getElementById('menu-english-primary-menu');
            var branding = document.querySelector('.site-branding');
            var extra = document.querySelector('.main-header-extra-class');
            if (!nav || !branding || !extra) return;

            var links = nav.querySelectorAll('li > a');
            nav.style.fontSize = '';
            links.forEach(function (a) { a.style.paddingLeft = ''; a.style.paddingRight = ''; });

            function isWrapped() {
                return extra.getBoundingClientRect().top > branding.getBoundingClientRect().bottom - 4;
            }

            var size = parseFloat(getComputedStyle(nav).fontSize);
            var minSize = 10;   // px floor -- never shrink past readable
            var pad = links.length ? (parseFloat(getComputedStyle(links[0]).paddingLeft) || 0) : 0;
            var minPad = 4;
            var attempts = 0;
            while (isWrapped() && (size > minSize || pad > minPad) && attempts < 60) {
                if (size > minSize) { size -= 0.5; nav.style.fontSize = size + 'px'; }
                if (pad > minPad) {
                    pad -= 1;
                    links.forEach(function (a) { a.style.paddingLeft = pad + 'px'; a.style.paddingRight = pad + 'px'; });
                }
                attempts++;
            }
        }

        document.addEventListener('DOMContentLoaded', function () {

            var sel = document.getElementById('language-select');

            // Add every visible language (from the registry) not already an option.
            // Adding/removing a language from the dropdown is now just flipping its
            // "visible" flag via the dashboard -- no code change, ever.
            if (sel) {
                var vals = Array.from(sel.options).map(function(o){ return o.value; });
                Object.keys(LANGS).forEach(function (code) {
                    var lang = LANGS[code];
                    if (!lang.visible || vals.indexOf(code) !== -1) return;
                    var opt = document.createElement('option');
                    opt.value = code;
                    opt.textContent = lang.native || lang.name;
                    sel.appendChild(opt);
                });
            }

            // Inject audio button next to select
            injectAudioBtn();

            // Restore saved language from cookie
            var savedLang = getCookie('language');
            if (savedLang && ['mr','en','hi','gj','ta','te','ml','kn','bn','pa'].indexOf(savedLang) !== -1) {
                if (sel) sel.value = savedLang;
                updateAudioForLang(savedLang);
                applyUiI18n(savedLang);
                syncPillButtons((savedLang === 'gj') ? 'gu' : savedLang);
            } else {
                applyUiI18n('mr');   // page default before any selection
            }
            fitNavToOneLine();

            // Hook into existing select change — add audio update on top
            if (sel) {
                sel.addEventListener('change', function () {
                    updateAudioForLang(sel.value);
                    applyUiI18n(sel.value);
                    fitNavToOneLine();
                });
            }

            // Wire in-page .lang-btn pills (single-temple.php)
            document.querySelectorAll('.lang-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var lang = btn.dataset.lang;
                    var mappedLang = (lang === 'gu') ? 'gj' : lang;
                    if (sel) {
                        sel.value = mappedLang;
                        if (typeof toggleLanguage === 'function') toggleLanguage(mappedLang);
                    }
                    updateAudioForLang(mappedLang);
                    applyUiI18n(mappedLang);
                    fitNavToOneLine();
                    syncPillButtons(lang);
                });
            });
        });

        // Re-check after full page load too (fonts can shift text width after
        // the DOMContentLoaded measurement above).
        window.addEventListener('load', fitNavToOneLine);

        function injectAudioBtn() {
            var sel = document.getElementById('language-select');
            if (!sel || document.getElementById('pilgrim-audio-btn')) return;
            var wrap = document.createElement('span');
            wrap.id = 'lang-audio-wrap';
            sel.parentNode.insertBefore(wrap, sel);
            wrap.appendChild(sel);
            var btn = document.createElement('button');
            btn.id = 'pilgrim-audio-btn';
            btn.setAttribute('aria-label', 'Play audio');
            btn.setAttribute('type', 'button');
            btn.innerHTML = '&#128266;';
            if (!IS_TEMPLE) btn.classList.add('hidden');
            btn.addEventListener('click', function (e) { e.stopPropagation(); toggleAudio(); });
            wrap.appendChild(btn);
        }

        function syncPillButtons(lang) {
            document.querySelectorAll('.lang-btn').forEach(function (btn) {
                var isActive = btn.dataset.lang === lang;
                btn.classList.toggle('active', isActive);
                btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
        }

        function updateAudioForLang(lang) {
            var url      = AUDIO[lang] || '';
            var audioEl = document.getElementById('temple-audio-player');
            var playerEl = document.getElementById('temple-audio-player');
            var srcEl2   = document.getElementById('temple-audio-source');
            var audioMsg = document.getElementById('audio-unavailable');

       if (playerEl && !playerEl.paused) {
    playerEl.pause();
    setPlayState(false);
}

            if (playerEl && srcEl2) {
                if (url) {
                    srcEl2.src = url;
                    playerEl.load();
                    playerEl.style.display = 'block';
                    if (audioMsg) audioMsg.style.display = 'none';
                } else {
                    playerEl.pause();
                    playerEl.style.display = 'none';
                    if (audioMsg) audioMsg.style.display = 'block';
                }
            }
        }

        function toggleAudio() {
            var sel     = document.getElementById('language-select');
            var lang    = sel ? sel.value : 'mr';
            var url     = AUDIO[lang] || '';
            var audioEl = document.getElementById('pilgrim-global-audio');
            var srcEl   = document.getElementById('pilgrim-audio-src');

            if (!url) {
                var btn = document.getElementById('pilgrim-audio-btn');
                if (btn) { btn.innerHTML = '&#128263;'; setTimeout(function(){ btn.innerHTML = '&#128266;'; }, 1200); }
                return;
            }
            if (srcEl && srcEl.src !== url) { srcEl.src = url; audioEl.load(); }
            if (audioEl.paused) {
                audioEl.play().then(function(){ setPlayState(true); }).catch(function(){ setPlayState(false); });
            } else {
                audioEl.pause(); setPlayState(false);
            }
        }

        function setPlayState(playing) {
            var btn = document.getElementById('pilgrim-audio-btn');
            if (!btn) return;
            btn.classList.toggle('playing', playing);
            btn.innerHTML = playing ? '&#9646;&#9646;' : '&#128266;';
            btn.setAttribute('aria-label', playing ? 'Pause audio' : 'Play audio');
        }

        document.addEventListener('DOMContentLoaded', function () {
            var audioEl = document.getElementById('pilgrim-global-audio');
            if (audioEl) audioEl.addEventListener('ended', function(){ setPlayState(false); });
        });

        function getCookie(name) {
            var nameEQ = name + '=';
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {
                var c = ca[i].trim();
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length);
            }
            return null;
        }
    })();
    </script>

    <?php
}

// Override marquee slider with 4-language version

function temple_marquee_slider_shortcode_v2() {
    ob_start();
    $temple_query = new WP_Query(array(
        'post_type'      => 'temple',
        'posts_per_page' => 10,
        'post_status'    => 'publish',
    ));
    if ( $temple_query->have_posts() ) : ?>
        <style>
        .temple-marquee-wrapper { overflow: hidden; position: relative; width: 100%; background: #e4965030; padding: 15px 0; }
        .temple-marquee-track { display: flex; width: max-content; animation: marqueeScroll 60s linear infinite; }
        .temple-marquee-item { flex: 0 0 auto; width: 200px; margin-right: 15px; text-align: center; }
        .slider-post-feature-image { width: 100%; height: 125px; background-position: center; background-size: cover; background-repeat: no-repeat; margin-bottom: 7px; }
        .temple-marquee-item h4 { font-size: 12px; color: #333; margin: 0; }
        .temple-marquee-item a { text-decoration: none; color: inherit; }
        @keyframes marqueeScroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .temple-marquee-wrapper:hover .temple-marquee-track { animation-play-state: paused; }
        @media (max-width: 600px) { .temple-marquee-item { width: 150px; } .slider-post-feature-image { height: 100px; } }
        </style>
        <div class="temple-marquee-wrapper">
            <div class="temple-marquee-track">
                <?php for ( $i = 0; $i < 2; $i++ ) :
                    $temple_query->rewind_posts();
                    while ( $temple_query->have_posts() ) : $temple_query->the_post(); ?>
                        <div class="temple-marquee-item">
                            <a href="<?php echo esc_url( get_permalink() ); ?>" target="_blank">
                                <div class="slider-post-feature-image" style="background-image: url('<?php echo esc_url( get_the_post_thumbnail_url() ); ?>');"></div>
                                <div class="mr_lang dis_lang" style="display:block;"><h4><?php echo esc_html( get_field('marathi_title') ?: get_the_title() ); ?></h4></div>
                                <div class="en_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('english_title') ?: get_the_title() ); ?></h4></div>
                                <div class="hi_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('hindi_title') ?: get_the_title() ); ?></h4></div>
                                <div class="gj_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('gujarati_title') ?: get_the_title() ); ?></h4></div>
                                <div class="ta_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('tamil_title') ?: get_the_title() ); ?></h4></div>
                                <div class="te_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('telugu_title') ?: get_the_title() ); ?></h4></div>
                                <div class="ml_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('malayalam_title') ?: get_the_title() ); ?></h4></div>
                                <div class="kn_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('kannada_title') ?: get_the_title() ); ?></h4></div>
                                <div class="bn_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('bengali_title') ?: get_the_title() ); ?></h4></div>
                                <div class="pa_lang dis_lang" style="display:none;"><h4><?php echo esc_html( get_field('punjabi_title') ?: get_the_title() ); ?></h4></div>
                            </a>
                        </div>
                    <?php endwhile;
                endfor;
                wp_reset_postdata(); ?>
            </div>
        </div>
    <?php endif;
    return ob_get_clean();
}

add_action( 'wp_footer', 'pilgrim_extend_language_and_audio', 20 );

remove_shortcode( 'temple_slider' );
add_shortcode( 'temple_slider', 'temple_marquee_slider_shortcode_v2' );
