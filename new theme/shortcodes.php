<?php
/**
 * Theme shortcodes (ported from Hello Elementor child).
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Every fixed piece of site text (headings, buttons, place names, footer) in
 * all site languages -- one place to change wording. Brand names are written in
 * each script, not translated.
 *
 * @return array<string, array<string, string>>
 */
function pds_i18n_strings() {
	static $strings = null;
	if ( null === $strings ) {
		$strings = array(
			'about_title' => array(
				'mr' => 'माहिती',
				'en' => 'About Us',
				'hi' => 'जानकारी',
				'gj' => 'અમારા વિશે',
				'ta' => 'எங்களை பற்றி',
				'te' => 'మా గురించి',
				'ml' => 'ഞങ്ങളെക്കുറിച്ച്',
				'kn' => 'ನಮ್ಮ ಬಗ್ಗೆ',
				'bn' => 'আমাদের সম্পর্কে',
				'pa' => 'ਸਾਡੇ ਬਾਰੇ',
			),
			'about_p1' => array(
				'mr' => 'भारत ही लौकिकतेबरोबरच पारलौकिक विचारांची, अर्थ आणि काम या पुरूषार्थांबरोबरच अध्यात्माचीही भूमी आहे. मातृस्वरूप नद्या, पर्वत, तीर्थक्षेत्रे ही येथील अध्यात्मिक धरोहर आहे. नानाविध देवालयांमुळे या भूमीस परम पावित्र्य लाभलेले आहे. धार्मिक महत्त्व, तसेच वैशिष्ट्यपूर्ण स्थापत्य यांनी यांतील अनेक मंदिरे भाविकांना साद घालीत असतात. आजच्या माहिती-तंत्रज्ञानाच्या आधुनिक युगातही या मंदिरांचे विविध पैलू अनेकांस अज्ञात आहेत.',
				'en' => 'India is not only a land of worldly prosperity but also a land of spiritual contemplation. It is a land that values both <em>Artha</em> (wealth), <em>Kama</em> (desire), and <em>Adhyatma</em> (spirituality). Rivers, mountains, and pilgrimage sites, which are revered in a motherly form, are an integral part of its rich spiritual heritage. The countless temples spread across this land have bestowed upon it the highest level of sanctity. Because of their religious significance and unique architectural beauty, many of these temples continue to attract and inspire devotees even today. Yet, even in today’s digital age, much about their history and spiritual importance remains unexplored.',
				'hi' => 'भारत न केवल सांसारिक सुखों की भूमि है, बल्कि आध्यात्मिक चिंतन की भी भूमि है। यह वह भूमि है जो अर्थ (धन), काम (इच्छा) और अध्यात्म (आध्यात्मिकता) दोनों को महत्व देती है। नदियाँ, पर्वत और तीर्थ स्थल, जिन्हें मातृ रूप में पूजा जाता है, इसकी समृद्ध आध्यात्मिक विरासत का हिस्सा हैं। इस भूमि पर फैले असंख्य मंदिरों ने इसे सर्वोच्च पवित्रता प्रदान की है। अपने धार्मिक महत्व और विशिष्ट वास्तुकला के कारण, इनमें से कई मंदिर आज भी भक्तों को आकर्षित और प्रेरित करते हैं। फिर भी, आज के डिजिटल युग में भी, इनके इतिहास और आध्यात्मिक महत्व के बारे में बहुत कुछ अनछुआ ही है।',
				'gj' => 'ભારત માત્ર સાંસારિક સમૃદ્ધિની ભૂમિ જ નથી, પરંતુ આધ્યાત્મિક ચિંતનની પણ ભૂમિ છે. આ એક એવી ભૂમિ છે જે અર્થ, કામ અને અધ્યાત્મ ત્રણેયનું મૂલ્ય સમજે છે. નદીઓ, પર્વતો અને તીર્થસ્થાનો, જેમને માતૃસ્વરૂપે પૂજવામાં આવે છે, તે તેના સમૃદ્ધ આધ્યાત્મિક વારસાનો અભિન્ન અંગ છે. આ સમગ્ર ભૂમિ પર ફેલાયેલા અસંખ્ય મંદિરોએ તેને સર્વોચ્ચ પવિત્રતા અર્પણ કરી છે. તેમના ધાર્મિક મહત્વ અને અદભૂત સ્થાપત્ય કલાને કારણે, આમાંના ઘણા મંદિરો આજે પણ ભક્તોને આકર્ષિત અને પ્રેરિત કરે છે. તેમ છતાં, આજના ડિજિટલ યુગમાં પણ, તેમના ઇતિહાસ અને આધ્યાત્મિક મહત્વ વિશે ઘણું બધું અન્વેષણ કરવાનું બાકી છે.',
				'ta' => 'இந்தியா உலகியல் செழிப்பு மிக்க நிலம் மட்டுமல்ல, ஆன்மீகச் சிந்தனைக்கும் உறைவிடமாகும். இது அர்த்தம் (செல்வம்), காமம் (விருப்பம்) மற்றும் அத்யாத்மா (ஆன்மீகம்) ஆகிய மூன்றையும் போற்றும் பூமியாகும். தாயாகக் கருதப்படும் ஆறுகள், மலைகள் மற்றும் புனிதத் தலங்கள் ஆகியவை இதன் வளமான ஆன்மீக பாரம்பரியத்தின் பிரிக்க முடியாத அங்கங்களாகும். இந்நிலம் முழுவதும் பரவியுள்ள எண்ணற்ற ஆலயங்கள், இதற்கு மிக உயர்ந்த புனிதத்தன்மையை வழங்கியுள்ளன. அவற்றின் மத முக்கியத்துவம் மற்றும் தனித்துவமான கட்டடக்கலை அழகு காரணமாக, இக்கோயில்களில் பல இன்றும் பக்தர்களை ஈர்த்தும், ஊக்கப்படுத்தியும் வருகின்றன. இருப்பினும், இன்றைய டிஜிட்டல் யுகத்திலும், அவற்றின் வரலாறு மற்றும் ஆன்மீக முக்கியத்துவம் குறித்த பல தகவல்கள் இன்னும் ஆராயப்படாமலேயே உள்ளன.',
				'te' => 'భారతదేశం కేవలం లౌకిక సంపదకు నిలయమే కాకుండా, ఆధ్యాత్మిక చింతనకు కూడా పుట్టినిల్లు. ఇది అర్థం, కామం మరియు ఆధ్యాత్మికత అనే మూడింటికి సమాన ప్రాధాన్యతనిచ్చే పుణ్యభూమి. మాతృ స్వరూపాలుగా ఆరాధించబడే నదులు, పర్వతాలు మరియు తీర్థయాత్ర స్థలాలు ఈ దేశపు గొప్ప ఆధ్యాత్మిక వారసత్వంలో అంతర్భాగాలు. ఈ భూమి అంతటా విస్తరించి ఉన్న అసంఖ్యాక దేవాలయాలు దీనికి అత్యున్నత స్థాయి పవిత్రతను చేకూర్చాయి. వాటి మతపరమైన ప్రాముఖ్యత మరియు విశిష్టమైన శిల్పకళా సౌందర్యం కారణంగా, ఈ దేవాలయాలలో చాలా వరకు నేటికీ భక్తులను ఆకర్షిస్తూ, ఉత్తేజపరుస్తూనే ఉన్నాయి. అయినప్పటికీ, నేటి డిజిటల్ యుగంలో కూడా, వాటి చరిత్ర మరియు ఆధ్యాత్మిక ప్రాముఖ్యతకు సంబంధించిన అనేక విషయాలు ఇంకా అన్వేషించబడవలసి ఉన్నాయి.',
				'ml' => 'ഭാരതം ഭൗതിക സമൃദ്ധിയുടെ നാട് മാത്രമല്ല, ആത്മീയ ചിന്തകളുടെ കൂടി നാടാണ്. അർത്ഥം, കാമം, അധ്യാത്മം എന്നീ മൂന്നിനും തുല്യ പ്രാധാന്യം നൽകുന്ന നാടാണിത്. മാതൃരൂപത്തിൽ ആരാധിക്കപ്പെടുന്ന നദികളും പർവതങ്ങളും തീർത്ഥാടന കേന്ദ്രങ്ങളും ഭാരതത്തിന്റെ സമ്പന്നമായ ആത്മീയ പൈതൃകത്തിന്റെ അവിഭാജ്യ ഘടകങ്ങളാണ്. ഈ മണ്ണിലുടനീളം വ്യാപിച്ചുകിടക്കുന്ന അസംഖ്യം ക്ഷേത്രങ്ങൾ ഇതിന് അതീവ പരിശുദ്ധി നൽകുന്നു. അവയുടെ മതപരമായ പ്രാധാന്യവും അതുല്യമായ വാസ്തുവിദ്യാ സൗന്ദര്യവും കാരണം, അനേകം ക്ഷേത്രങ്ങൾ ഇന്നും ഭക്തരെ ആകർഷിക്കുകയും പ്രചോദിപ്പിക്കുകയും ചെയ്യുന്നു. എന്നിരുന്നാലും, ഇന്നത്തെ ഡിജിറ്റൽ യുഗത്തിലും അവയുടെ ചരിത്രത്തെയും ആത്മീയ പ്രാധാന്യത്തെയും കുറിച്ചുള്ള പല കാര്യങ്ങളും ഇന്നും അജ്ഞാതമായി തുടരുന്നു.',
				'kn' => 'ಭಾರತವು ಕೇವಲ ಲೌಕಿಕ ಸಮೃದ್ಧಿಯ ನಾಡಲ್ಲ, ಬದಲಾಗಿ ಆಧ್ಯಾತ್ಮಿಕ ಚಿಂತನೆಯ ತವರೂರು. ಇದು ಅರ್ಥ, ಕಾಮ ಮತ್ತು ಅಧ್ಯಾತ್ಮ - ಈ ಮೂರಕ್ಕೂ ಸಮಾನ ಮನ್ನಣೆ ನೀಡುವ ಪುಣ್ಯಭೂಮಿ. ಮಾತೃಸ್ವರೂಪದಲ್ಲಿ ಪೂಜಿಸಲ್ಪಡುವ ನದಿಗಳು, ಪರ್ವತಗಳು ಮತ್ತು ತೀರ್ಥಕ್ಷೇತ್ರಗಳು ಈ ನಾಡಿನ ಶ್ರೀಮಂತ ಆಧ್ಯಾತ್ಮಿಕ ಪರಂಪರೆಯ ಅವಿಭಾಜ್ಯ ಅಂಗಗಳಾಗಿವೆ. ಈ ನಾಡಿನಾದ್ಯಂತ ಹರಡಿರುವ ಅಸಂಖ್ಯಾತ ದೇವಾಲಯಗಳು ಇದಕ್ಕೆ ಅತ್ಯುನ್ನತ ಪಾವಿತ್ರ್ಯತೆಯನ್ನು ತಂದುಕೊಟ್ಟಿವೆ. ತಮ್ಮ ಧಾರ್ಮಿಕ ಮಹತ್ವ ಮತ್ತು ಅದ್ವಿತೀಯ ವಾಸ್ತುಶಿಲ್ಪದ ಸೌಂದರ್ಯದಿಂದಾಗಿ, ಇಂದಿಗೂ ಈ ದೇವಾಲಯಗಳು ಭಕ್ತರನ್ನು ಆಕರ್ಷಿಸುತ್ತಾ ಮತ್ತು ಪ್ರೇರೇಪಿಸುತ್ತಾ ಬಂದಿವೆ. ಆದರೂ, ಇಂದಿನ ಡಿಜಿಟಲ್ ಯುಗದಲ್ಲೂ ಇವುಗಳ ಇತಿಹಾಸ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕ ಮಹತ್ವದ ಕುರಿತಾದ ಅನೇಕ ವಿಷಯಗಳು ಇನ್ನೂ ಅನ್ವೇಷಣೆಯ ಹಂತದಲ್ಲೇ ಉಳಿದಿವೆ.',
				'bn' => 'ভারত কেবল পার্থিব সমৃদ্ধির ভূমিই নয়, বরং আধ্যাত্মিক চিন্তারও এক পীঠস্থান। এটি এমন এক দেশ যা অর্থ, কাম এবং অধ্যাত্ম—এই তিনটিরই গুরুত্ব স্বীকার করে। নদী, পর্বত এবং তীর্থস্থানসমূহ, যেগুলোকে মাতৃরূপে পূজা করা হয়, তা এই দেশের সমৃদ্ধ আধ্যাত্মিক ঐতিহ্যের অবিচ্ছেদ্য অংশ। এই ভূখণ্ড জুড়ে ছড়িয়ে থাকা অগণিত মন্দির একে সর্বোচ্চ পবিত্রতায় ভূষিত করেছে। তাদের ধর্মীয় তাৎপর্য এবং অনন্য স্থাপত্যশৈলীর কারণে, এই মন্দিরগুলোর অনেকগুলোই আজও ভক্তদের আকৃষ্ট ও অনুপ্রাণিত করে চলেছে। তবুও, আজকের ডিজিটাল যুগেও, এদের ইতিহাস ও আধ্যাত্মিক গুরুত্বের অনেক কিছুই এখনো অনাবিষ্কৃত রয়ে গেছে।',
				'pa' => 'ਭਾਰਤ ਕੇਵਲ ਦੁਨਿਆਵੀ ਖੁਸ਼ਹਾਲੀ ਦੀ ਹੀ ਧਰਤੀ ਨਹੀਂ, ਸਗੋਂ ਅਧਿਆਤਮਿਕ ਚਿੰਤਨ ਦੀ ਵੀ ਧਰਤੀ ਹੈ। ਇਹ ਇੱਕ ਅਜਿਹੀ ਧਰਤੀ ਹੈ ਜੋ ਅਰਥ, ਕਾਮ ਅਤੇ ਅਧਿਆਤਮ, ਤਿੰਨਾਂ ਨੂੰ ਮਹੱਤਵ ਦਿੰਦੀ ਹੈ। ਨਦੀਆਂ, ਪਹਾੜ ਅਤੇ ਤੀਰਥ ਸਥਾਨ, ਜਿਨ੍ਹਾਂ ਨੂੰ ਮਾਂ ਦੇ ਰੂਪ ਵਿੱਚ ਪੂਜਿਆ ਜਾਂਦਾ ਹੈ, ਇਸਦੀ ਅਮੀਰ ਅਧਿਆਤਮਿਕ ਵਿਰਾਸਤ ਦਾ ਅਨਿੱਖੜਵਾਂ ਅੰਗ ਹਨ। ਇਸ ਧਰਤੀ \'ਤੇ ਫੈਲੇ ਅਣਗਿਣਤ ਮੰਦਰਾਂ ਨੇ ਇਸਨੂੰ ਸਰਵਉੱਚ ਪਵਿੱਤਰਤਾ ਪ੍ਰਦਾਨ ਕੀਤੀ ਹੈ। ਆਪਣੀ ਧਾਰਮਿਕ ਮਹੱਤਤਾ ਅਤੇ ਵਿਲੱਖਣ ਵਾਸਤੂਕਲਾ ਸੁੰਦਰਤਾ ਦੇ ਕਾਰਨ, ਇਹਨਾਂ ਵਿੱਚੋਂ ਬਹੁਤ ਸਾਰੇ ਮੰਦਰ ਅੱਜ ਵੀ ਸ਼ਰਧਾਲੂਆਂ ਨੂੰ ਆਕਰਸ਼ਿਤ ਅਤੇ ਪ੍ਰੇਰਿਤ ਕਰਦੇ ਹਨ। ਫਿਰ ਵੀ, ਅੱਜ ਦੇ ਡਿਜੀਟਲ ਯੁੱਗ ਵਿੱਚ ਵੀ, ਉਹਨਾਂ ਦੇ ਇਤਿਹਾਸ ਅਤੇ ਅਧਿਆਤਮਿਕ ਮਹੱਤਵ ਬਾਰੇ ਬਹੁਤ ਕੁਝ ਅਣਗੌਲਿਆ ਰਹਿ ਗਿਆ ਹੈ।',
			),
			'about_p2' => array(
				'mr' => 'ईश्वरी आशीर्वाद आणि दैवी शांततेच्या शोधात असणाऱ्या भाविकांना अशा खास देवस्थानांची, त्यांच्या धार्मिक महत्तेची आणि वैशिष्ट्यांची ओळख करून देणे हीसुद्धा एक ईश्वरसेवाच. याच भावनेने या संकेतस्थळावरून देशभरातील विविध धार्मिक वैशिष्ट्यांनी नटलेल्या मंदिरांची, तीर्थस्थानांची माहिती देण्याचा आमचा संकल्प आहे. सादर आहे त्यातीलच ही काही मंदिरांची माहिती…',
				'en' => 'Introducing devotees to such sacred temples is itself a noble act of service to the Divine. Through this platform, we strive to connect devotees seeking divine blessings and inner peace with these holy places—celebrating their faith, cultural values, and the grandeur of their architectural heritage. Here, you will find information about some of the most remarkable temples of India, each reflecting the country’s enduring spiritual spirit.',
				'hi' => 'भक्तों को ऐसे पवित्र मंदिरों से परिचित कराना स्वयं ईश्वर की सेवा का एक महान कार्य है। इस मंच के माध्यम से, हम दिव्य आशीर्वाद और आंतरिक शांति की तलाश करने वाले भक्तों को इन पवित्र स्थलों से जोड़ने का प्रयास करते हैं - इनके विश्वास, सांस्कृतिक मूल्य और स्थापत्य कला की भव्यता का जश्न मनाते हुए। यहाँ, आपको भारत के कुछ सबसे उल्लेखनीय मंदिरों की जानकारी मिलेगी, जिनमें से प्रत्येक देश की चिरस्थायी आध्यात्मिक भावना का प्रतिबिंब है…',
				'gj' => 'ભક્તોને આવા પવિત્ર મંદિરોથી પરિચિત કરાવવા એ પોતે જ ઈશ્વરની એક ઉમદા સેવા છે. આ મંચના માધ્યમથી, અમે દિવ્ય આશીર્વાદ અને આંતરિક શાંતિની શોધમાં રહેલા ભક્તોને આ પવિત્ર સ્થળો સાથે જોડવાનો પ્રયાસ કરીએ છીએ—જે તેમની શ્રદ્ધા, સાંસ્કૃતિક મૂલ્યો અને તેમની સ્થાપત્ય કલાના ભવ્ય વારસાની ઉજવણી કરે છે. અહીં, તમને ભારતના કેટલાક સૌથી અદભૂત મંદિરો વિશેની માહિતી મળશે, જે દરેક દેશની ચિરંતન આધ્યાત્મિક ભાવનાને પ્રતિબિંબિત કરે છે.',
				'ta' => 'இத்தகைய புனிதமான ஆலயங்களை பக்தர்களுக்கு அறிமுகப்படுத்துவதே இறைவனுக்குச் செய்யும் உன்னதமான தொண்டாகும். இந்தத் தளத்தின் வாயிலாக, இறைவனின் அருளையும் மன அமைதியையும் தேடும் பக்தர்களை இப்புனிதத் தலங்களுடன் இணைக்க நாங்கள் முயல்கிறோம்—அவர்களின் நம்பிக்கை, கலாச்சார விழுமியங்கள் மற்றும் கட்டடக்கலைப் பாரம்பரியத்தின் பிரம்மாண்டத்தைப் போற்றுகிறோம். இந்தியாவின் மிகச்சிறந்த ஆலயங்கள் குறித்த தகவல்களை இங்கே நீங்கள் காணலாம்; இவை ஒவ்வொன்றும் இந்நாட்டின் அழியாத ஆன்மீக உணர்வைப் பிரதிபலிக்கின்றன.',
				'te' => 'భక్తులకు ఇటువంటి పవిత్ర దేవాలయాలను పరిచయం చేయడం దైవానికి చేసే ఒక గొప్ప సేవ. ఈ వేదిక ద్వారా, దైవానుగ్రహాన్ని మరియు అంతర్గత ప్రశాంతతను కోరుకునే భక్తులను ఈ పుణ్యక్షేత్రాలతో అనుసంధానించడానికి మేము కృషి చేస్తున్నాము—వారి విశ్వాసాన్ని, సాంస్కృతిక విలువలను మరియు వారి నిర్మాణ వారసత్వ వైభవాన్ని చాటిచెబుతున్నాము. ఇక్కడ, మీరు భారతదేశంలోని అత్యంత విశిష్టమైన కొన్ని దేవాలయాల గురించి సమాచారాన్ని కనుగొంటారు, వీటిలో ప్రతి ఒక్కటి దేశం యొక్క చిరకాల ఆధ్యాత్మిక స్ఫూర్తిని ప్రతిబింబిస్తాయి.',
				'ml' => 'ഇത്തരം പുണ്യക്ഷേത്രങ്ങളെ ഭക്തർക്ക് പരിചയപ്പെടുത്തുന്നത് തന്നെ ഈശ്വരന് ചെയ്യുന്ന ഉദാത്തമായ ഒരു സേവനമാണ്. ദൈവിക അനുഗ്രഹങ്ങളും ആത്മശാന്തിയും തേടുന്ന ഭക്തരെ ഈ പുണ്യസ്ഥലങ്ങളുമായി ബന്ധിപ്പിക്കാൻ ഈ പ്ലാറ്റ്‌ഫോമിലൂടെ ഞങ്ങൾ പരിശ്രമിക്കുന്നു—അവരുടെ വിശ്വാസത്തെയും സാംസ്കാരിക മൂല്യങ്ങളെയും വാസ്തുവിദ്യാ പൈതൃകത്തിന്റെ പ്രൗഢിയെയും ഞങ്ങൾ ഇതിലൂടെ ആഘോഷിക്കുന്നു. ഭാരതത്തിന്റെ അനശ്വരമായ ആത്മീയ ചൈതന്യത്തെ പ്രതിഫലിപ്പിക്കുന്ന, ഏറ്റവും ശ്രദ്ധേയമായ ചില ക്ഷേത്രങ്ങളെക്കുറിച്ചുള്ള വിവരങ്ങൾ നിങ്ങൾക്ക് ഇവിടെ കണ്ടെത്താം.',
				'kn' => 'ಇಂತಹ ಪವಿತ್ರ ದೇವಾಲಯಗಳನ್ನು ಭಕ್ತರಿಗೆ ಪರಿಚಯಿಸುವುದೇ ದೈವಕ್ಕೆ ಸಲ್ಲಿಸುವ ಒಂದು ಶ್ರೇಷ್ಠ ಸೇವೆಯಾಗಿದೆ. ಈ ವೇದಿಕೆಯ ಮೂಲಕ, ದೈವಿಕ ಆಶೀರ್ವಾದ ಮತ್ತು ಆಂತರಿಕ ಶಾಂತಿಯನ್ನು ಬಯಸುವ ಭಕ್ತರನ್ನು ಈ ಪುಣ್ಯಕ್ಷೇತ್ರಗಳೊಂದಿಗೆ ಸಂಪರ್ಕಿಸಲು ನಾವು ಪ್ರಯತ್ನಿಸುತ್ತಿದ್ದೇವೆ—ಅವರ ನಂಬಿಕೆ, ಸಾಂಸ್ಕೃತಿಕ ಮೌಲ್ಯಗಳು ಮತ್ತು ವಾಸ್ತುಶಿಲ್ಪದ ಪರಂಪರೆಯ ವೈಭವವನ್ನು ಸಂಭ್ರಮಿಸುತ್ತಿದ್ದೇವೆ. ಇಲ್ಲಿ, ನೀವು ಭಾರತದ ಅತ್ಯಂತ ಗಮನಾರ್ಹವಾದ ಕೆಲವು ದೇವಾಲಯಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿಯನ್ನು ಕಾಣಬಹುದು, ಇವು ಪ್ರತಿಯೊಂದೂ ದೇಶದ ಅಚಲವಾದ ಆಧ್ಯಾತ್ಮಿಕ ಚೈತನ್ಯವನ್ನು ಪ್ರತಿಬಿಂಬಿಸುತ್ತವೆ.',
				'bn' => 'ভক্তদের এমন পবিত্র মন্দিরের সাথে পরিচিত করা নিজেই পরমেশ্বরের প্রতি সেবার এক মহৎ কাজ। এই প্ল্যাটফর্মের মাধ্যমে, আমরা সেইসব ভক্তদের এই পবিত্র স্থানগুলোর সাথে সংযুক্ত করার চেষ্টা করি যারা ঐশ্বরিক আশীর্বাদ এবং অন্তরের শান্তি খুঁজছেন—তাদের বিশ্বাস, সাংস্কৃতিক মূল্যবোধ এবং স্থাপত্য ঐতিহ্যের মহিমাকে উদযাপন করছি। এখানে, আপনি ভারতের সবচেয়ে উল্লেখযোগ্য কিছু মন্দির সম্পর্কে তথ্য পাবেন, যার প্রতিটিই দেশের চিরন্তন আধ্যাত্মিক চেতনাকে প্রতিফলিত করে।',
				'pa' => 'ਸ਼ਰਧਾਲੂਆਂ ਨੂੰ ਅਜਿਹੇ ਪਵਿੱਤਰ ਮੰਦਰਾਂ ਨਾਲ ਜਾਣੂ ਕਰਵਾਉਣਾ ਆਪਣੇ ਆਪ ਵਿੱਚ ਪ੍ਰਭੂ ਦੀ ਇੱਕ ਨੇਕ ਸੇਵਾ ਹੈ। ਇਸ ਮੰਚ ਰਾਹੀਂ, ਅਸੀਂ ਉਨ੍ਹਾਂ ਸ਼ਰਧਾਲੂਆਂ ਨੂੰ ਜੋ ਦੈਵੀ ਆਸ਼ੀਰਵਾਦ ਅਤੇ ਅੰਦਰੂਨੀ ਸ਼ਾਂਤੀ ਦੀ ਭਾਲ ਵਿੱਚ ਹਨ, ਇਹਨਾਂ ਪਵਿੱਤਰ ਸਥਾਨਾਂ ਨਾਲ ਜੋੜਨ ਦਾ ਯਤਨ ਕਰਦੇ ਹਾਂ—ਉਨ੍ਹਾਂ ਦੀ ਆਸਥਾ, ਸੱਭਿਆਚਾਰਕ ਕਦਰਾਂ-ਕੀਮਤਾਂ ਅਤੇ ਉਨ੍ਹਾਂ ਦੀ ਵਾਸਤੂਕਲਾ ਦੇ ਵਿਰਸੇ ਦੀ ਸ਼ਾਨ ਦਾ ਜਸ਼ਨ ਮਨਾਉਂਦੇ ਹੋਏ। ਇੱਥੇ, ਤੁਹਾਨੂੰ ਭਾਰਤ ਦੇ ਕੁਝ ਸਭ ਤੋਂ ਸ਼ਾਨਦਾਰ ਮੰਦਰਾਂ ਬਾਰੇ ਜਾਣਕਾਰੀ ਮਿਲੇਗੀ, ਜਿਨ੍ਹਾਂ ਵਿੱਚੋਂ ਹਰ ਇੱਕ ਦੇਸ਼ ਦੀ ਸਦੀਵੀ ਅਧਿਆਤਮਿਕ ਭਾਵਨਾ ਨੂੰ ਦਰਸਾਉਂਦਾ ਹੈ।',
			),
			'famous_title' => array(
				'mr' => 'अध्यात्मिक शोधकांसाठी प्रसिद्ध मंदिरे',
				'en' => 'Famous Temples for Spiritual Explorers',
				'hi' => 'आध्यात्मिक खोजकर्ताओं के लिए प्रसिद्ध मंदिर',
				'gj' => 'આધ્યાત્મિક ખોજીઓ માટે પ્રસિદ્ધ મંદિરો',
				'ta' => 'ஆன்மீகத் தேடலில் உள்ளவர்களுக்கான புகழ்பெற்ற திருக்கோயில்கள்',
				'te' => 'ఆధ్యాత్మిక అన్వేషకుల కోసం ప్రసిద్ధ దేవాలయాలు',
				'ml' => 'ആത്മീയ സഞ്ചാരികൾക്കായി പ്രശസ്തമായ ക്ഷേത്രങ്ങൾ',
				'kn' => 'ಆಧ್ಯಾತ್ಮಿಕ ಅನ್ವೇಷಕರಿಗಾಗಿ ಪ್ರಸಿದ್ಧ ದೇವಾಲಯಗಳು',
				'bn' => 'আধ্যাত্মিক অভিযাত্রীদের জন্য বিখ্যাত মন্দিরসমূহ',
				'pa' => 'ਅਧਿਆਤਮਿਕ ਖੋਜੀਆਂ ਲਈ ਪ੍ਰਸਿੱਧ ਮੰਦਰ',
			),
			'gallery_title' => array(
				'mr' => 'फोटो गॅलरी',
				'en' => 'Photo Gallery',
				'hi' => 'चित्र दीर्घा',
				'gj' => 'ફોટો ગેલેરી',
				'ta' => 'புகைப்படத் தொகுப்பு',
				'te' => 'ఫోటో గ్యాలరీ',
				'ml' => 'ചിത്രശാല',
				'kn' => 'ಛಾಯಾಚಿತ್ರ ಗ್ಯಾಲರಿ',
				'bn' => 'ফটো গ্যালারি',
				'pa' => 'ਤਸਵੀਰ ਗੈਲਰੀ',
			),
			'temples' => array(
				'mr' => 'मंदिरे',
				'en' => 'Temples',
				'hi' => 'मंदिर',
				'gj' => 'મંદિરો',
				'ta' => 'கோவில்கள்',
				'te' => 'దేవాలయాలు',
				'ml' => 'ക്ഷേത്രങ്ങൾ',
				'kn' => 'ದೇವಾಲಯಗಳು',
				'bn' => 'মন্দিরসমূহ',
				'pa' => 'ਮੰਦਿਰ',
			),
			'other_cities' => array(
				'mr' => 'इतर शहरे',
				'en' => 'Other Cities',
				'hi' => 'अन्य शहर',
				'gj' => 'અન્ય શહેરો',
				'ta' => 'பிற நகரங்கள்',
				'te' => 'ఇతర నగరాలు',
				'ml' => 'മറ്റ് നഗരങ്ങൾ',
				'kn' => 'ಇತರ ನಗರಗಳು',
				'bn' => 'অন্যান্য শহর',
				'pa' => 'ਹੋਰ ਸ਼ਹਿਰ',
			),
			'view_more' => array(
				'mr' => 'अधिक पहा',
				'en' => 'View More',
				'hi' => 'और देखें',
				'gj' => 'વધુ જુઓ',
				'ta' => 'மேலும் காண்க',
				'te' => 'మరిన్ని చూడండి',
				'ml' => 'കൂടുതൽ കാണുക',
				'kn' => 'ಇನ್ನಷ್ಟು ವೀಕ್ಷಿಸಿ',
				'bn' => 'আরও দেখুন',
				'pa' => 'ਹੋਰ ਵੇਖੋ',
			),
			'view_details' => array(
				'mr' => 'अधिक माहिती',
				'en' => 'View Details',
				'hi' => 'विवरण देखें',
				'gj' => 'વિગત જુઓ',
				'ta' => 'விவரங்களைக் காண்க',
				'te' => 'వివరాలను చూడండి',
				'ml' => 'വിശദാംശങ്ങൾ കാണുക',
				'kn' => 'ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಿ',
				'bn' => 'বিস্তারিত দেখুন',
				'pa' => 'ਵੇਰਵੇ ਦੇਖੋ',
			),
			'st_maharashtra' => array(
				'mr' => 'महाराष्ट्र',
				'en' => 'Maharashtra',
				'hi' => 'महाराष्ट्र',
				'gj' => 'મહારાષ્ટ્ર',
				'ta' => 'மகாராஷ்டிரம்',
				'te' => 'మహారాష్ట్ర',
				'ml' => 'മഹാരാഷ്ട്ര',
				'kn' => 'ಮಹಾರಾಷ್ಟ್ರ',
				'bn' => 'মহারাষ্ট্র',
				'pa' => 'ਮਹਾਰਾਸ਼ਟਰ',
			),
			'st_gujarat' => array(
				'mr' => 'गुजरात',
				'en' => 'Gujarat',
				'hi' => 'गुजरात',
				'gj' => 'ગુજરાત',
				'ta' => 'குஜராத்',
				'te' => 'గుజరాత్',
				'ml' => 'ഗുജറാത്ത്',
				'kn' => 'ಗುಜರಾತ್',
				'bn' => 'গুজরাত',
				'pa' => 'ਗੁਜਰਾਤ',
			),
			'st_madhya-pradesh' => array(
				'mr' => 'मध्य प्रदेश',
				'en' => 'Madhya Pradesh',
				'hi' => 'मध्य प्रदेश',
				'gj' => 'મધ્ય પ્રદેશ',
				'ta' => 'மத்தியப் பிரதேசம்',
				'te' => 'మధ్యప్రదేశ్',
				'ml' => 'മധ്യപ്രദേശ്',
				'kn' => 'ಮಧ್ಯಪ್ರದೇಶ',
				'bn' => 'মধ্যপ্রদেশ',
				'pa' => 'ਮੱਧ ਪ੍ਰਦੇਸ਼',
			),
			'st_goa' => array(
				'mr' => 'गोवा',
				'en' => 'Goa',
				'hi' => 'गोवा',
				'gj' => 'ગોવા',
				'ta' => 'கோவா',
				'te' => 'గోవా',
				'ml' => 'ഗോവ',
				'kn' => 'ಗೋವಾ',
				'bn' => 'গোয়া',
				'pa' => 'ਗੋਆ',
			),
			'ct_pune' => array(
				'mr' => 'पुणे',
				'en' => 'Pune',
				'hi' => 'पुणे',
				'gj' => 'પુણે',
				'ta' => 'புணே',
				'te' => 'పుణె',
				'ml' => 'പുണെ',
				'kn' => 'ಪುಣೆ',
				'bn' => 'পুণে',
				'pa' => 'ਪੁਣੇ',
			),
			'ct_mumbai' => array(
				'mr' => 'मुंबई',
				'en' => 'Mumbai',
				'hi' => 'मुंबई',
				'gj' => 'મુંબઈ',
				'ta' => 'மும்பை',
				'te' => 'ముంబై',
				'ml' => 'മുംബൈ',
				'kn' => 'ಮುಂಬೈ',
				'bn' => 'মুম্বাই',
				'pa' => 'ਮੁੰਬਈ',
			),
			'ct_nashik' => array(
				'mr' => 'नाशिक',
				'en' => 'Nashik',
				'hi' => 'नासिक',
				'gj' => 'નાશિક',
				'ta' => 'நாசிக்',
				'te' => 'నాసిక్',
				'ml' => 'നാസിക്',
				'kn' => 'ನಾಸಿಕ್',
				'bn' => 'নাসিক',
				'pa' => 'ਨਾਸਿਕ',
			),
			'ct_satara' => array(
				'mr' => 'सातारा',
				'en' => 'Satara',
				'hi' => 'सतारा',
				'gj' => 'સાતારા',
				'ta' => 'சதாரா',
				'te' => 'సతారా',
				'ml' => 'സതാര',
				'kn' => 'ಸತಾರಾ',
				'bn' => 'সাতারা',
				'pa' => 'ਸਤਾਰਾ',
			),
			'ct_solapur' => array(
				'mr' => 'सोलापूर',
				'en' => 'Solapur',
				'hi' => 'सोलापुर',
				'gj' => 'સોલાપુર',
				'ta' => 'சோலாப்பூர்',
				'te' => 'సోలాపూర్',
				'ml' => 'സോലാപൂർ',
				'kn' => 'ಸೋಲಾಪುರ',
				'bn' => 'সোলাপুর',
				'pa' => 'ਸੋਲਾਪੁਰ',
			),
			'ct_kolhapur' => array(
				'mr' => 'कोल्हापूर',
				'en' => 'Kolhapur',
				'hi' => 'कोल्हापुर',
				'gj' => 'કોલ્હાપુર',
				'ta' => 'கோலாப்பூர்',
				'te' => 'కొల్హాపూర్',
				'ml' => 'കൊൽഹാപ്പൂർ',
				'kn' => 'ಕೊಲ್ಲಾಪುರ',
				'bn' => 'কোলহাপুর',
				'pa' => 'ਕੋਲਹਾਪੁਰ',
			),
			'g_ozar' => array(
				'mr' => 'विघ्नहर्ता गणेश मंदिर, ओझर, पुणे',
				'en' => 'Vignaharta Ganesh Temple, Ozar, Pune',
				'hi' => 'विघ्नहर्ता गणेश मंदिर, ओझर, पुणे',
				'gj' => 'વિઘ્નહર્તા ગણેશ મંદિર, ઓઝર, પુણે',
				'ta' => 'விக்னஹர்த்தா கணபதி கோவில், ஓஸர், புணே',
				'te' => 'విఘ్నహర్త గణేశ దేవాలయం, ఓజార్, పుణె',
				'ml' => 'വിഘ്നഹർത്ത ഗണപതി ക്ഷേത്രം, ഓസർ, പുണെ',
				'kn' => 'ವಿಘ್ನಹರ್ತ ಗಣೇಶ ದೇವಸ್ಥಾನ, ಓಜರ್, ಪುಣೆ',
				'bn' => 'বিঘ্নহর্তা গণেশ মন্দির, ওজার, পুণে',
				'pa' => 'ਵਿਘਨਹਰਤਾ ਗਣੇਸ਼ ਮੰਦਰ, ਓਜ਼ਰ, ਪੁਣੇ',
			),
			'g_tarkeshwar' => array(
				'mr' => 'तारकेश्वर मंदिर, पुणे',
				'en' => 'Tarkeshwar Temple, Pune',
				'hi' => 'तारकेश्वर मंदिर, पुणे',
				'gj' => 'તર્કેશ્વર મંદિર, પુણે',
				'ta' => 'தாரகேஷ்வர் கோயில், புணே',
				'te' => 'తర్కేశ్వర్ ఆలయం, పుణె',
				'ml' => 'തർക്കേശ്വർ ക്ഷേത്രം, പുണെ',
				'kn' => 'ತರ್ಕೇಶ್ವರ ದೇವಾಲಯ, ಪುಣೆ',
				'bn' => 'তারকেশ্বর মন্দির, পুণে',
				'pa' => 'ਤਰਕੇਸ਼ਵਰ ਮੰਦਰ, ਪੁਣੇ',
			),
			'g_mallikarjun' => array(
				'mr' => 'मल्लिकार्जुन मंदिर, लोणी-भापकर, पुणे',
				'en' => 'Mallikarjun Temple, Loni-Bhapkar, Pune',
				'hi' => 'मल्लिकार्जुन मंदिर, लोणी-भापकर, पुणे',
				'gj' => 'મલ્લિકાર્જુન મંદિર, લોણી-ભાપકર, પુણે',
				'ta' => 'மல்லிகார்ஜுனன் கோயில், லோனி-பாப்கர், புணே',
				'te' => 'మల్లికార్జున దేవాలయం, లోని-భప్కర్, పుణె',
				'ml' => 'മല്ലികാർജുന ക്ഷേത്രം, ലോണി-ഭപ്കർ, പുണെ',
				'kn' => 'ಮಲ್ಲಿಕಾರ್ಜುನ ದೇವಾಲಯ, ಲೋಣಿ-ಭಾಪ್ಕರ್, ಪುಣೆ',
				'bn' => 'মল্লিকার্জুন মন্দির, লোনি-ভপকর, পুণে',
				'pa' => 'ਮੱਲਿਕਾਰਜੁਨ ਮੰਦਰ, ਲੋਨੀ-ਭਾਪਕਰ, ਪੁਣੇ',
			),
			'g_purandar' => array(
				'mr' => 'पुरंदर मंदिर, पुणे',
				'en' => 'Purandar Temple, Pune',
				'hi' => 'पुरंदर मंदिर, पुणे',
				'gj' => 'પુરંદર મંદિર, પુણે',
				'ta' => 'புரந்தர் கோயில், புணே',
				'te' => 'పురందర్ ఆలయం, పుణె',
				'ml' => 'പുരന്ദർ ക്ഷേത്രം, പുണെ',
				'kn' => 'ಪುರಂದರ ದೇವಾಲಯ, ಪುಣೆ',
				'bn' => 'পুরন্দর মন্দির, পুণে',
				'pa' => 'ਪੁਰੰਦਰ ਮੰਦਰ, ਪੁਣੇ',
			),
			'g_vitthal' => array(
				'mr' => 'विठ्ठल मंदिर, दौंड, पुणे',
				'en' => 'Vitthal Mandir, Daund, Pune',
				'hi' => 'विठ्ठल मंदिर, दौंड, पुणे',
				'gj' => 'વિઠ્ઠલ મંદિર, દૌંડ, પુણે',
				'ta' => 'விட்டல் மந்திர், தௌண்ட், புணே',
				'te' => 'విఠల్ మందిరం, దౌండ్, పుణె',
				'ml' => 'വിഠൽ മന്ദിർ, ദൗണ്ട്, പുണെ',
				'kn' => 'ವಿಠ್ಠಲ ಮಂದಿರ, ದೌಂಡ್, ಪುಣೆ',
				'bn' => 'বিঠল মন্দির, দৌণ্ড, পুণে',
				'pa' => 'ਵਿੱਠਲ ਮੰਦਰ, ਦੌਂਡ, ਪੁਣੇ',
			),
			'privacy' => array(
				'mr' => 'गोपनीयता',
				'en' => 'Privacy Policy',
				'hi' => 'गोपनीयता नीति',
				'gj' => 'ગોપનીયતા નીતિ',
				'ta' => 'தனியுரிமைக் கொள்கை',
				'te' => 'గోప్యతా విధానం',
				'ml' => 'സ്വകാര്യതാ നയം',
				'kn' => 'ಗೌಪ್ಯತಾ ನೀತಿ',
				'bn' => 'গোপনীয়তা নীতি',
				'pa' => 'ਪਰਦੇਦਾਰੀ ਨੀਤੀ',
			),
			'terms' => array(
				'mr' => 'अटी व शर्ती',
				'en' => 'Terms & Conditions',
				'hi' => 'नियम एवं शर्तें',
				'gj' => 'નિયમો અને શરતો',
				'ta' => 'விதிமுறைகள் மற்றும் நிபந்தனைகள்',
				'te' => 'నిబంధనలు మరియు షరతులు',
				'ml' => 'നിബന്ധനകളും വ്യവസ്ഥകളും',
				'kn' => 'ನಿಯಮಗಳು ಮತ್ತು ಷರತ್ತುಗಳು',
				'bn' => 'শর্তাবলী',
				'pa' => 'ਨਿਯਮ ਅਤੇ ਸ਼ਰਤਾਂ',
			),
			'instagram' => array(
				'mr' => 'इंस्टाग्राम',
				'en' => 'Instagram',
				'hi' => 'इंस्टाग्राम',
				'gj' => 'ઇન્સ્ટાગ્રામ',
				'ta' => 'இன்ஸ்டாகிராம்',
				'te' => 'ఇన్‌స్టాగ్రామ్',
				'ml' => 'ഇൻസ്റ്റാഗ്രാം',
				'kn' => 'ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್',
				'bn' => 'ইনস্টাগ্রাম',
				'pa' => 'ਇੰਸਟਾਗ੍ਰਾਮ',
			),
			'facebook' => array(
				'mr' => 'फेसबुक',
				'en' => 'Facebook',
				'hi' => 'फेसबुक',
				'gj' => 'ફેસબુક',
				'ta' => 'முகநூல்',
				'te' => 'ఫేస్‌బుక్',
				'ml' => 'ഫേസ്‌ബുക്ക്',
				'kn' => 'ಫೇಸ್‌ಬುಕ್',
				'bn' => 'ফেসবুক',
				'pa' => 'ਫੇਸਬੁੱਕ',
			),
			'youtube' => array(
				'mr' => 'यूट्यूब',
				'en' => 'YouTube',
				'hi' => 'यूट्यूब',
				'gj' => 'યુટ્યુબ',
				'ta' => 'யூடியூப்',
				'te' => 'యూట్యూబ్',
				'ml' => 'യൂട്യൂബ്',
				'kn' => 'ಯೂಟ್ಯೂಬ್',
				'bn' => 'ইউটিউব',
				'pa' => 'ਯੂਟਿਊਬ',
			),
			'rights' => array(
				'mr' => 'पिलग्रिम डेटा सर्व्हिसेस | सर्व हक्क राखीव.',
				'en' => 'Pilgrim Data Services | All Rights Reserved.',
				'hi' => 'पिलग्रिम डेटा सर्विसेस | सर्वाधिकार सुरक्षित।',
				'gj' => 'પિલગ્રિમ ડેટા સર્વિસિસ | સર્વ હક્ક સ્વાધીન.',
				'ta' => 'பில்கிரிம் டேட்டா சர்வீசஸ் | அனைத்து உரிமைகளும் பாதுகாக்கப்பட்டவை.',
				'te' => 'పిల్‌గ్రిమ్ డేటా సర్వీసెస్ | సర్వ హక్కులు ప్రత్యేకించబడినవి.',
				'ml' => 'പിൽഗ്രിം ഡാറ്റ സർവീസസ് | സർവ്വ അവകാശങ്ങളും നിക്ഷിപ്തം.',
				'kn' => 'ಪಿಲ್‌ಗ್ರಿಮ್ ಡೇಟಾ ಸರ್ವೀಸಸ್ | ಸರ್ವ ಹಕ್ಕುಗಳನ್ನು ಕಾಯ್ದಿರಿಸಲಾಗಿದೆ.',
				'bn' => 'পিলগ্রিম ডেটা সার্ভিসেস | সর্বস্বত্ব সংরক্ষিত।',
				'pa' => 'ਪਿਲਗ੍ਰਿਮ ਡੇਟਾ ਸਰਵਿਸਿਜ਼ | ਸਾਰੇ ਹੱਕ ਰਾਖਵੇਂ ਹਨ।',
			),
			'unavailable' => array(
				'mr' => 'ही मंदिर माहिती मराठीत उपलब्ध नाही.',
				'en' => 'This temple information is not available in English.',
				'hi' => 'यह मंदिर जानकारी हिन्दी में उपलब्ध नहीं है।',
				'gj' => 'આ મંદિરની માહિતી ગુજરાતીમાં ઉપલબ્ધ નથી.',
				'ta' => 'இந்தக் கோயில் குறித்த தகவல்கள் தமிழில் கிடைக்கவில்லை.',
				'te' => 'ఈ ఆలయ సమాచారం తెలుగులో అందుబాటులో లేదు.',
				'ml' => 'ഈ ക്ഷേത്രത്തെക്കുറിച്ചുള്ള വിവരങ്ങൾ മലയാളത്തിൽ ലഭ്യമല്ല.',
				'kn' => 'ಈ ದೇವಾಲಯದ ಮಾಹಿತಿಯು ಕನ್ನಡದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.',
				'bn' => 'এই মন্দিরের তথ্য বাংলা ভাষায় উপলব্ধ নেই।',
				'pa' => 'ਇਸ ਮੰਦਰ ਬਾਰੇ ਜਾਣਕਾਰੀ ਪੰਜਾਬੀ ਵਿੱਚ ਉਪਲਬਧ ਨਹੀਂ ਹੈ।',
			),
		);
	}
	return $strings;
}

/**
 * One fixed string in one language, falling back to English (so a language
 * added to pds_get_temple_languages() later shows English, never a blank).
 *
 * @param string $key  pds_i18n_strings() key.
 * @param string $code Language code.
 * @return string
 */
function pds_t( $key, $code ) {
	$strings = pds_i18n_strings();
	if ( ! empty( $strings[ $key ][ $code ] ) ) {
		return $strings[ $key ][ $code ];
	}
	return isset( $strings[ $key ]['en'] ) ? $strings[ $key ]['en'] : '';
}

/**
 * The same text once per site language, in the markup the language switcher
 * toggles: <tag class="{code}_lang dis_lang">. Marathi shows by default.
 *
 * @param string $key     pds_i18n_strings() key.
 * @param string $tag     Wrapper element.
 * @param string $class   Extra classes before the language class.
 * @param string $display Display value for the default (Marathi) block.
 * @param string $inner   Optional element to wrap the text in (e.g. h3).
 * @return string
 */
function pds_lang_blocks( $key, $tag = 'span', $class = '', $display = 'block', $inner = '' ) {
	$html = '';
	foreach ( array_keys( pds_get_temple_languages() ) as $code ) {
		$text = esc_html( pds_t( $key, $code ) );
		if ( $inner ) {
			$text = '<' . $inner . '>' . $text . '</' . $inner . '>';
		}
		$html .= sprintf(
			'<%1$s class="%2$s%3$s_lang dis_lang" style="display: %4$s;">%5$s</%1$s>',
			$tag,
			$class ? esc_attr( $class ) . ' ' : '',
			esc_attr( $code ),
			'mr' === $code ? $display : 'none',
			$text
		);
	}
	return $html;
}

/**
 * The temple popup's "not available in this language" text only ships four
 * languages (inc/enqueue.php); the other six fell back to an English sentence.
 * Add the missing ones without overwriting any it already has.
 */
function pds_temple_popup_i18n() {
	$missing = array();
	foreach ( array_keys( pds_get_temple_languages() ) as $code ) {
		$missing[ $code ] = pds_t( 'unavailable', $code );
	}
	wp_add_inline_script(
		'pds-temple-popup',
		'if(window.pdsTemplePopup&&pdsTemplePopup.i18n){pdsTemplePopup.i18n.unavailable=Object.assign(' . wp_json_encode( $missing ) . ',pdsTemplePopup.i18n.unavailable||{});}',
		'before'
	);
}
add_action( 'wp_enqueue_scripts', 'pds_temple_popup_i18n', 100 );

/**
 * [search_bar]
 */
function pds_search_bar_shortcode() {
	ob_start();
	?>
	<form role="search" method="get" class="search-form" action="<?php echo esc_url( home_url( '/' ) ); ?>">
		<input type="search" class="search-field" placeholder="<?php echo esc_attr_x( 'Search Temple', 'placeholder', 'pilgrim-data-services' ); ?>" value="" name="s" />
		<?php
		wp_dropdown_categories(
			array(
				'taxonomy'         => 'city',
				'value_field'      => 'slug',
				'name'             => 'city',
				'show_option_none' => __( 'Select City', 'pilgrim-data-services' ),
				'option_none_value'=> '0',
				'orderby'          => 'parent',
				'order'            => 'ASC',
				'hierarchical'     => 1,
				'hide_empty'       => 0,
			)
		);
		?>
		<input type="hidden" name="post_type" value="temple" />
		<button type="submit" id="searchsubmit" value="Search"><?php esc_html_e( 'SEARCH', 'pilgrim-data-services' ); ?></button>
	</form>
	<?php
	return ob_get_clean();
}
add_shortcode( 'search_bar', 'pds_search_bar_shortcode' );

/**
 * [temple_grid]
 */
function pds_temple_grid_shortcode( $atts ) {
	$atts = shortcode_atts(
		array(
			'posts_per_page' => 6,
			'paged'          => get_query_var( 'paged' ) ? get_query_var( 'paged' ) : 1,
		),
		$atts,
		'temple_grid'
	);

	$query = new WP_Query(
		array(
			'post_type'      => 'temple',
			'posts_per_page' => (int) $atts['posts_per_page'],
			'paged'          => (int) $atts['paged'],
		)
	);

	ob_start();
	?>
	<div>
		<?php if ( $query->have_posts() ) : ?>
			<div class="temple-grid-format">
				<?php
				while ( $query->have_posts() ) :
					$query->the_post();
					?>
					<div class="temple-block">
						<div class="temple-data">
							<a href="<?php the_permalink(); ?>" <?php pds_the_temple_link_attrs(); ?>>
								<div class="post-feature-image" style="background-image: url('<?php echo esc_url( get_the_post_thumbnail_url() ); ?>');"></div>
								<?php foreach ( array_keys( pds_get_temple_languages() ) as $pds_code ) : ?>
									<div class="<?php echo esc_attr( $pds_code ); ?>_lang dis_lang" style="display: <?php echo 'mr' === $pds_code ? 'block' : 'none'; ?>;">
										<h5><?php echo esc_html( pds_get_temple_language_title( get_the_ID(), $pds_code ) ); ?></h5>
										<span class="view-details-btn"> <?php echo esc_html( pds_t( 'view_details', $pds_code ) ); ?> </span>
									</div>
								<?php endforeach; ?>
								<?php the_excerpt(); ?>
							</a>
						</div>
					</div>
				<?php endwhile; ?>
			</div>
		<?php else : ?>
			<p><?php esc_html_e( 'No Temples Found', 'pilgrim-data-services' ); ?></p>
		<?php endif; ?>
	</div>
	<?php
	wp_reset_postdata();
	return ob_get_clean();
}
add_shortcode( 'temple_grid', 'pds_temple_grid_shortcode' );

/**
 * [lightslider_looper]
 */
function pds_lightslider_looper_shortcode() {
	$images = pds_get_field( 'gallery', false, array() );
	if ( empty( $images ) || ! is_array( $images ) ) {
		return '';
	}

	ob_start();
	?>
	<div class="tl_slide_photo_container">
		<ul id="light-slider" class="image-gallery">
			<?php foreach ( $images as $image ) : ?>
				<li data-thumb="<?php echo esc_url( $image['url'] ); ?>">
					<a href="<?php echo esc_url( $image['url'] ); ?>" data-fancybox="gallery" data-caption="<?php echo esc_attr( $image['alt'] ?? '' ); ?>">
						<img src="<?php echo esc_url( $image['url'] ); ?>" alt="<?php echo esc_attr( $image['alt'] ?? '' ); ?>" />
					</a>
				</li>
			<?php endforeach; ?>
		</ul>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode( 'lightslider_looper', 'pds_lightslider_looper_shortcode' );

/**
 * [temple_search_filter]
 */
function pds_temple_search_filter_shortcode() {
	ob_start();
	?>
	<form id="temple-filter-form" class="search-form" method="GET" action="<?php echo esc_url( home_url( '/' ) ); ?>">
		<select id="parent-city" name="parent_city">
			<option value=""><?php esc_html_e( 'Select State', 'pilgrim-data-services' ); ?></option>
			<?php
			$parent_terms = get_terms(
				array(
					'taxonomy'   => 'city',
					'parent'     => 0,
					'hide_empty' => false,
				)
			);
			if ( ! is_wp_error( $parent_terms ) ) {
				foreach ( $parent_terms as $term ) {
					echo '<option value="' . esc_attr( $term->slug ) . '">' . esc_html( $term->name ) . '</option>';
				}
			}
			?>
		</select>
		<select name="city" id="child-city">
			<option value=""><?php esc_html_e( 'Select District', 'pilgrim-data-services' ); ?></option>
		</select>
		<input class="search-field" type="text" name="s" placeholder="<?php esc_attr_e( 'Temples Name', 'pilgrim-data-services' ); ?>" value="<?php echo esc_attr( get_search_query() ); ?>" />
		<input type="hidden" name="post_type" value="temple" />
		<button type="submit" id="searchsubmit" value="Search"><?php esc_html_e( 'SEARCH', 'pilgrim-data-services' ); ?></button>
	</form>
	<?php
	return ob_get_clean();
}
add_shortcode( 'temple_search_filter', 'pds_temple_search_filter_shortcode' );

/**
 * [temple_slider] marquee
 */
function pds_temple_slider_shortcode() {
	$query = new WP_Query(
		array(
			'post_type'      => 'temple',
			'posts_per_page' => 30,
			'post_status'    => 'publish',
		)
	);

	if ( ! $query->have_posts() ) {
		return '';
	}

	ob_start();
	?>
	<style>
	.temple-marquee-wrapper { overflow: hidden; position: relative; width: 100%; background: #e4965030; padding: 15px 0; }
	.temple-marquee-track { display: flex; width: max-content; animation: marqueeScroll 60s linear infinite; }
	.temple-marquee-item { flex: 0 0 auto; width: 200px; margin-right: 15px; text-align: center; }
	.slider-post-feature-image { width: 100%; height: 125px; background-position: center; background-size: cover; background-repeat: no-repeat; margin-bottom: 7px; }
	.temple-marquee-item h4 { font-size: 12px; color: #333; margin: 0; }
	.temple-marquee-item a { text-decoration: none; color: inherit; }
	@keyframes marqueeScroll { 0% { transform: translateX(0); } 100% { transform: translateX(-15%); } }
	.temple-marquee-wrapper:hover .temple-marquee-track { animation-play-state: paused; }
	@media (max-width: 600px) {
		.temple-marquee-item { width: 150px; }
		.slider-post-feature-image { height: 100px; }
	}
	</style>
	<div class="temple-marquee-wrapper">
		<div class="temple-marquee-track">
			<?php
			for ( $i = 0; $i < 2; $i++ ) :
				$query->rewind_posts();
				while ( $query->have_posts() ) :
					$query->the_post();
					?>
					<div class="temple-marquee-item">
						<a href="<?php the_permalink(); ?>" <?php pds_the_temple_link_attrs(); ?>>
							<?php if ( has_post_thumbnail() ) : ?>
								<div class="slider-post-feature-image" style="background-image: url('<?php echo esc_url( get_the_post_thumbnail_url() ); ?>');"></div>
							<?php endif; ?>
							<?php foreach ( array_keys( pds_get_temple_languages() ) as $pds_code ) : ?>
								<div class="<?php echo esc_attr( $pds_code ); ?>_lang dis_lang" style="display: <?php echo 'mr' === $pds_code ? 'block' : 'none'; ?>;"><h4><?php echo esc_html( pds_get_temple_language_title( get_the_ID(), $pds_code ) ); ?></h4></div>
							<?php endforeach; ?>
						</a>
					</div>
					<?php
				endwhile;
			endfor;
			wp_reset_postdata();
			?>
		</div>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode( 'temple_slider', 'pds_temple_slider_shortcode' );
