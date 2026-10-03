<?php
/**
 * Homepage content sections (shared by front-page.php and Home Page template).
 * Layout matched to https://allowing-lion-dev.10web.cloud/
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$uploads = content_url( '/uploads' );

$states = array(
	array(
		'slug'  => 'maharashtra',
		'image' => $uploads . '/2025/03/Maharashtra.png',
		'label' => 'st_maharashtra',
	),
	array(
		'slug'  => 'gujarat',
		'image' => $uploads . '/2025/03/Gujarat-1-1.png',
		'label' => 'st_gujarat',
	),
	array(
		'slug'  => 'madya-pradesh',
		'image' => $uploads . '/2025/11/mp-map.png',
		'label' => 'st_madhya-pradesh',
	),
	array(
		'slug'  => 'goa',
		'image' => $uploads . '/2025/11/goa.png',
		'label' => 'st_goa',
	),
);

$cities = array(
	array(
		'slug'  => 'pune',
		'image' => $uploads . '/2024/05/Group-2384.png',
		'label' => 'ct_pune',
	),
	array(
		'slug'  => 'mumbai',
		'image' => $uploads . '/2024/05/Group-2387.png',
		'label' => 'ct_mumbai',
	),
	array(
		'slug'  => 'nashik',
		'image' => $uploads . '/2024/05/Group-2403-1.png',
		'label' => 'ct_nashik',
	),
	array(
		'slug'  => 'satara',
		'image' => $uploads . '/2024/05/Group-2406-1.png',
		'label' => 'ct_satara',
	),
	array(
		'slug'  => 'solapur',
		'image' => $uploads . '/2024/05/Group-2405-1.png',
		'label' => 'ct_solapur',
	),
	array(
		'slug'  => 'kolhapur',
		'image' => $uploads . '/2024/05/Group-2404-1.png',
		'label' => 'ct_kolhapur',
	),
);

$featured_temples = array(
	array(
		'image' => $uploads . '/2024/01/स्वामी-नारायण-6.jpeg',
		'url'   => home_url( '/temple/swaminarayan-temple-narhe-ambegaon-road-narhe-pune/' ),
		'title' => array(
			'mr' => 'स्वामीनारायण मंदिर नऱ्हे-आंबेगाव',
			'en' => 'Swaminarayan Temple Narhe',
			'hi' => 'स्वामीनारायण मंदिर नऱ्हे-आंबेगाव',
		),
	),
	array(
		'image' => $uploads . '/2024/06/Tarkeshwar-temple-Yerawda1.jpg',
		'url'   => home_url( '/temple/tarakeshwar-mahadev-temple-yerwada-pune/' ),
		'title' => array(
			'mr' => 'तारकेश्वर महादेव मंदिर',
			'en' => 'Tarakeshwar Mahadev Temple',
			'hi' => 'तारकेश्वर महादेव मंदिर',
		),
	),
	array(
		'image' => $uploads . '/2024/09/1.-1-1.png',
		'url'   => home_url( '/temple/ram-mandir-tulshibagh-pune/' ),
		'title' => array(
			'mr' => 'राम मंदिर तुळशीबाग',
			'en' => 'Ram Mandir Tulshibag',
			'hi' => 'राम मंदिर तुळशीबाग',
		),
	),
	array(
		'image' => $uploads . '/2024/09/8.-1.png',
		'url'   => home_url( '/temple/moraya-gosavi-mandir-chinchwad-pune/' ),
		'title' => array(
			'mr' => 'मोरया गोसावी मंदिर',
			'en' => 'Moraya Gosavi Mandir',
			'hi' => 'मोरया गोसावी मंदिर',
		),
	),
	array(
		'image' => $uploads . '/2024/11/4.-1-8.png',
		'url'   => home_url( '/temple/merulinga-mahadev-merulinga-ph-d-javali-dist-satara/' ),
		'title' => array(
			'mr' => 'मेरुलिंग महादेव मंदिर',
			'en' => 'Merulinga Mahadev Mandir',
			'hi' => 'मेरुलिंग महादेव मंदिर',
		),
	),
	array(
		'image' => $uploads . '/2025/12/2-44-1.jpeg',
		'url'   => home_url( '/temple/mahaganapati-dholya-temple-wai-ta-wai-dist-satara/' ),
		'title' => array(
			'mr' => 'महागणपती (ढोल्या) मंदिर',
			'en' => 'Mahaganapati Dholya Temple',
			'hi' => 'महागणपती (ढोल्या) मंदिर',
		),
	),
);

$gallery_images = array(
	array(
		'image' => $uploads . '/2024/06/IMG_3183.jpg',
		'title' => 'g_ozar',
	),
	array(
		'image' => $uploads . '/2024/06/IMG_2393-min.jpg',
		'title' => 'g_ozar',
	),
	array(
		'image' => $uploads . '/2024/06/Tarkeshwar-temple-Yerawda8-1.jpg',
		'title' => 'g_tarkeshwar',
	),
	array(
		'image' => $uploads . '/2024/06/मल्लिकार्जू-मंदिर-लोणी-भापकर10-min.jpg',
		'title' => 'g_mallikarjun',
	),
	array(
		'image' => $uploads . '/2024/06/Purandar-Temple1-min.png',
		'title' => 'g_purandar',
	),
	array(
		'image' => $uploads . '/2024/06/IMG_3684.jpg',
		'title' => 'g_vitthal',
	),
);

$other_cities_url = home_url( '/city/maharashtra/' );
$listing_pages    = get_pages(
	array(
		'meta_key'   => '_wp_page_template',
		'meta_value' => 'temple-listing.php',
		'number'     => 1,
	)
);
if ( ! empty( $listing_pages ) ) {
	$other_cities_url = get_permalink( $listing_pages[0]->ID );
}

$view_more_url = $other_cities_url;
?>

<main id="content" class="site-main pilgrim-home">

	<!-- Hero (full width) -->
	<section class="ph-hero ph-full" aria-label="<?php esc_attr_e( 'Temples in India', 'pilgrim-data-services' ); ?>">
		<picture>
			<source media="(max-width: 767px)" srcset="<?php echo esc_url( $uploads . '/2025/03/Banner-Design-Mobile-Background.png' ); ?>">
			<img
				class="ph-hero__image"
				src="<?php echo esc_url( $uploads . '/2024/05/Banner-Design-023.jpg' ); ?>"
				alt="<?php esc_attr_e( 'Temples in India', 'pilgrim-data-services' ); ?>"
				width="1920"
				height="750"
				fetchpriority="high"
			>
		</picture>
		<!-- <div class="ph-hero__search frm-back">
			< ?php echo do_shortcode( '[dcs_search]' ); ?>
		</div> -->
	</section>

	<!-- Temple marquee (full width) -->
	<section class="ph-marquee ph-full" aria-label="<?php esc_attr_e( 'Temple highlights', 'pilgrim-data-services' ); ?>">
		<?php echo do_shortcode( '[temple_slider]' ); ?>
	</section>

	<!-- About + explore -->
	<section class="ph-about" id="about">
		<div class="ph-container">
			<div class="ph-about__intro">
				<?php foreach ( array_keys( pds_get_temple_languages() ) as $pds_code ) : ?>
					<div class="<?php echo esc_attr( $pds_code ); ?>_lang dis_lang" style="display: <?php echo 'mr' === $pds_code ? 'block' : 'none'; ?>;">
						<h2 class="ph-section-title"><?php echo esc_html( pds_t( 'about_title', $pds_code ) ); ?></h2>
						<p><?php echo wp_kses_post( pds_t( 'about_p1', $pds_code ) ); ?></p>
						<p><?php echo wp_kses_post( pds_t( 'about_p2', $pds_code ) ); ?></p>
					</div>
				<?php endforeach; ?>
			</div>

			<div class="ph-explore about-cities">
				<div class="ph-states">
					<?php foreach ( $states as $state ) : ?>
						<a class="ph-explore__item" href="<?php echo esc_url( home_url( '/city/' . $state['slug'] . '/' ) ); ?>">
							<img src="<?php echo esc_url( $state['image'] ); ?>" alt="<?php echo esc_attr( pds_t( $state['label'], 'en' ) . ' | Temples in India' ); ?>" loading="lazy" width="190" height="152">
							<span class="ph-explore__caption widget-image-caption">
								<?php echo pds_lang_blocks( $state['label'] ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
							</span>
						</a>
					<?php endforeach; ?>
				</div>

				<div class="ph-cities">
					<?php foreach ( $cities as $city ) : ?>
						<a class="ph-explore__item" href="<?php echo esc_url( home_url( '/city/' . $city['slug'] . '/' ) ); ?>">
							<img src="<?php echo esc_url( $city['image'] ); ?>" alt="<?php echo esc_attr( pds_t( $city['label'], 'en' ) ); ?>" loading="lazy" width="190" height="152">
							<span class="ph-explore__caption widget-image-caption">
								<?php echo pds_lang_blocks( $city['label'] ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
							</span>
						</a>
					<?php endforeach; ?>
				</div>

				<div class="ph-explore__cta">
					<a class="ph-btn" href="<?php echo esc_url( $other_cities_url ); ?>">
						<?php echo pds_lang_blocks( 'other_cities', 'span', '', 'inline' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
					</a>
				</div>
			</div>
		</div>
	</section>

	<!-- Famous temples grid -->
	<section class="ph-famous" id="famous-temples">
		<div class="ph-container">
			<?php echo pds_lang_blocks( 'famous_title', 'h2', 'ph-section-title' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
			<?php echo do_shortcode( '[temple_grid]' ); ?>
		</div>
	</section>

	<!-- Promo banner -->
	<section class="ph-promo" aria-label="<?php esc_attr_e( 'Pilgrim Data', 'pilgrim-data-services' ); ?>">
		<div class="ph-container">
			<img
				src="<?php echo esc_url( $uploads . '/2025/03/PILGRIM-DATA-WEB-BANNER.gif' ); ?>"
				alt="<?php esc_attr_e( 'Pilgrim Data Services', 'pilgrim-data-services' ); ?>"
				loading="lazy"
			>
		</div>
	</section>

	<!-- Featured temple photos -->
	<!-- <section class="ph-featured">
		<div class="ph-container">
			<div class="ph-featured__grid">
				< ?php foreach ( $featured_temples as $temple ) : ?>
					<a class="ph-featured__item" href="< ?php echo esc_url( $temple['url'] ); ?>">
						<img src="< ?php echo esc_url( $temple['image'] ); ?>" alt="< ?php echo esc_attr( $temple['title']['en'] ); ?>" loading="lazy">
						<span class="ph-featured__caption widget-image-caption">
							<span class="mr_lang dis_lang" style="display: block;">< ?php echo esc_html( $temple['title']['mr'] ); ?></span>
							<span class="en_lang dis_lang" style="display: none;">< ?php echo esc_html( $temple['title']['en'] ); ?></span>
							<span class="hi_lang dis_lang" style="display: none;">< ?php echo esc_html( $temple['title']['hi'] ); ?></span>
						</span>
					</a>
				< ?php endforeach; ?>
			</div>
		</div>
	</section> -->

	<!-- Photo gallery -->
	<section class="ph-gallery gall" id="photo-gallery" aria-label="<?php esc_attr_e( 'Photo Gallery', 'pilgrim-data-services' ); ?>">
		<div class="ph-container">
			<?php echo pds_lang_blocks( 'gallery_title', 'h2', 'ph-section-title' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>

			<div class="ph-gallery__grid">
				<?php foreach ( $gallery_images as $item ) : ?>
					<a
						href="<?php echo esc_url( $item['image'] ); ?>"
						data-fancybox="home-gallery"
						data-caption="<?php echo esc_attr( pds_t( $item['title'], 'en' ) ); ?>"
						class="ph-gallery__item"
					>
						<img src="<?php echo esc_url( $item['image'] ); ?>" alt="<?php echo esc_attr( pds_t( $item['title'], 'en' ) ); ?>" loading="lazy">
						<span class="ph-gallery__caption">
							<?php echo pds_lang_blocks( $item['title'] ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
						</span>
					</a>
				<?php endforeach; ?>
			</div>

			<div class="ph-gallery__cta">
				<a class="ph-btn" href="<?php echo esc_url( $view_more_url ); ?>">
					<?php echo pds_lang_blocks( 'view_more', 'span', '', 'inline' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
				</a>
			</div>
		</div>
	</section>

</main>
