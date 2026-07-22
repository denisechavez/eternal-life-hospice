#!/usr/bin/env python3
"""
patch-cities.py — Eternal Life Hospice
Patches every existing city page to add:
  1. WebPage schema (after BreadcrumbList schema)
  2. Visible "Hospice Care in [City] at a Glance" section
  3. Resources section with how-to-choose-a-hospice link
  4. Sixth FAQ (if only 5 exist)
  5. Nearby-city cross-links in intro section

Run from repo root:
    python3 website/patch-cities.py
"""

import os, re, json

OUT_DIR = "website/elh-preview"

# ── City metadata: slug → (neighborhood_context, nearby_pages, unique_faq6_q, unique_faq6_a) ────
CITY_META = {
"agoura-hills": {
    "county":"Los Angeles County","subregion":"Conejo Valley",
    "neighborhood":"across Old Agoura, Morrison Ranch, Liberty Canyon, Chumash and the Lake Lindero area",
    "nearby_html": 'nearby <a href="hospice-westlake-village-ca">Westlake Village</a>, <a href="hospice-calabasas-ca">Calabasas</a> and <a href="hospice-malibu-ca">Malibu</a>.',
    "faq6q":"Is hospice at home realistic in the rural parts of Agoura Hills?",
    "faq6a":"Yes. Many Agoura Hills families live in hillside homes and rural corridors of the Santa Monica Mountains. Eternal Life Hospice serves those areas with the same level of care — our team travels to where the patient is, regardless of whether they are in a neighborhood or at the end of a canyon road.",
},
"alhambra": {
    "county":"Los Angeles County","subregion":"San Gabriel Valley",
    "neighborhood":"in private residences, board-and-care homes and assisted-living communities throughout the San Gabriel Valley",
    "nearby_html": 'nearby <a href="hospice-arcadia-ca">Arcadia</a>, <a href="hospice-pasadena-ca">Pasadena</a> and <a href="hospice-san-marino-ca">San Marino</a>.',
    "faq6q":"How does Eternal Life Hospice approach care for multigenerational families in Alhambra?",
    "faq6a":"Alhambra has many households where family caregiving spans generations and multiple family members may be involved in decisions. Our social workers and interdisciplinary team work to include everyone who matters, support the family structure already in place and communicate clearly across generations and, where helpful, across language preferences.",
},
"arcadia": {
    "county":"Los Angeles County","subregion":"San Gabriel Valley",
    "neighborhood":"across Arcadia's established residential neighborhoods and senior communities along the Baldwin Avenue corridor",
    "nearby_html": 'nearby <a href="hospice-alhambra-ca">Alhambra</a>, <a href="hospice-pasadena-ca">Pasadena</a> and <a href="hospice-san-marino-ca">San Marino</a>.',
    "faq6q":"Does Arcadia have assisted living or memory care facilities where hospice can be added?",
    "faq6a":"Yes. Arcadia has a notable number of assisted living communities and residential care facilities. Eternal Life Hospice works directly alongside facility staff to layer hospice services onto the care the patient already receives, without disrupting their existing relationships or routines.",
},
"beverly-hills": {
    "county":"Los Angeles County","subregion":"Westside",
    "neighborhood":"on the flats, in Trousdale Estates and North Beverly Hills, and in surrounding Westside communities",
    "nearby_html": 'nearby <a href="hospice-culver-city-ca">Culver City</a>, <a href="hospice-santa-monica-ca">Santa Monica</a> and <a href="hospice-west-hollywood-ca">West Hollywood</a>.',
    "faq6q":"How does Eternal Life Hospice approach privacy for Beverly Hills families?",
    "faq6a":"We approach every engagement with discretion. Our team arrives in unmarked vehicles when requested, communicates through designated family contacts and maintains strict confidentiality throughout the course of care. Beverly Hills families trust us with moments that are deeply private — we take that responsibility seriously.",
},
"burbank": {
    "county":"Los Angeles County","subregion":"East San Fernando Valley",
    "neighborhood":"across Burbank's Media District, Magnolia Park, Chandler Estates and residential neighborhoods",
    "nearby_html": 'nearby <a href="hospice-glendale-ca">Glendale</a>, <a href="hospice-studio-city-ca">Studio City</a> and <a href="hospice-north-hollywood-ca">North Hollywood</a>.',
    "faq6q":"Does Burbank's entertainment industry community create any unique hospice care needs?",
    "faq6a":"Burbank is home to many media industry professionals and their families, who often have complex scheduling needs and high expectations for coordination. Eternal Life Hospice is experienced working with busy households — our team communicates clearly, schedules visits to fit the family's rhythm and remains reachable at all hours for enrolled patients.",
},
"calabasas": {
    "county":"Los Angeles County","subregion":"Las Virgenes Corridor",
    "neighborhood":"across The Oaks, Park Moderne, Calabasas Park and the Las Virgenes corridor",
    "nearby_html": 'nearby <a href="hospice-agoura-hills-ca">Agoura Hills</a>, <a href="hospice-westlake-village-ca">Westlake Village</a> and <a href="hospice-woodland-hills-ca">Woodland Hills</a>.',
    "faq6q":"Can hospice care be delivered inside gated communities in Calabasas?",
    "faq6a":"Yes. Eternal Life Hospice staff are experienced with gated community protocols and work with property management and security teams to ensure seamless, respectful access for nursing visits, equipment delivery and all other care needs.",
},
"camarillo": {
    "county":"Ventura County","subregion":"Pleasant Valley",
    "neighborhood":"across Mission Oaks, Spanish Hills, Camarillo Springs and surrounding Pleasant Valley neighborhoods",
    "nearby_html": 'nearby <a href="hospice-thousand-oaks-ca">Thousand Oaks</a>, <a href="hospice-oxnard-ca">Oxnard</a> and <a href="hospice-ventura-ca">Ventura</a>.',
    "faq6q":"Camarillo has many active senior communities — can residents in those communities receive hospice?",
    "faq6a":"Yes. Hospice is fully compatible with senior retirement community living. When a resident needs a higher level of medical support, Eternal Life Hospice works alongside the community's care staff to layer hospice services in — without requiring the resident to leave their home.",
},
"canoga-park": {
    "county":"Los Angeles County","subregion":"West San Fernando Valley",
    "neighborhood":"along the Sherman Way corridor and Canoga Park's residential neighborhoods",
    "nearby_html": 'nearby <a href="hospice-chatsworth-ca">Chatsworth</a>, <a href="hospice-west-hills-ca">West Hills</a> and <a href="hospice-woodland-hills-ca">Woodland Hills</a>.',
    "faq6q":"Are there financial assistance options for hospice in Canoga Park for families uncertain about costs?",
    "faq6a":"Medicare Part A covers hospice care for eligible patients and most covered services have little to no out-of-pocket cost. Medi-Cal also covers hospice for eligible California residents. Eternal Life Hospice will clarify your specific coverage and any potential copayments clearly before enrollment so there are no financial surprises.",
},
"chatsworth": {
    "county":"Los Angeles County","subregion":"West San Fernando Valley",
    "neighborhood":"throughout Chatsworth's distinctive neighborhoods near Stoney Point, Chatsworth Park and the Santa Susana Pass foothills",
    "nearby_html": 'nearby <a href="hospice-canoga-park-ca">Canoga Park</a>, <a href="hospice-west-hills-ca">West Hills</a> and <a href="hospice-northridge-ca">Northridge</a>.',
    "faq6q":"Does Chatsworth's more rural character create challenges for hospice care delivery?",
    "faq6a":"No. Chatsworth's larger lots and more rural feel are familiar to our team. We serve patients throughout Chatsworth's distinctive landscape, including homes near the rock formations and the more spread-out residential areas near the foothills, with the same scheduled visits and 24/7 on-call access as any community we serve.",
},
"culver-city": {
    "county":"Los Angeles County","subregion":"Westside",
    "neighborhood":"across Fox Hills, Blair Hills, Sunkist Park and Culver City's established neighborhoods",
    "nearby_html": 'nearby <a href="hospice-santa-monica-ca">Santa Monica</a>, <a href="hospice-beverly-hills-ca">Beverly Hills</a> and <a href="hospice-west-hollywood-ca">West Hollywood</a>.',
    "faq6q":"What integrative comfort therapies does Eternal Life Hospice offer in Culver City?",
    "faq6a":"Eternal Life Hospice provides integrative comfort therapies as part of its whole-person care approach — including music therapy, pet companionship, massage and other evidence-aligned modalities. These are offered at no additional expense to the family and are provided for patient comfort and wellbeing, not as treatments for the underlying diagnosis.",
},
"encino": {
    "county":"Los Angeles County","subregion":"South San Fernando Valley",
    "neighborhood":"across Royal Oaks, Amestoy Estates and Encino's hillside and valley neighborhoods",
    "nearby_html": 'nearby <a href="hospice-sherman-oaks-ca">Sherman Oaks</a>, <a href="hospice-tarzana-ca">Tarzana</a> and <a href="hospice-studio-city-ca">Studio City</a>.',
    "faq6q":"Can hospice be provided in Encino's larger hillside homes and estates?",
    "faq6a":"Yes. Hospice care is delivered wherever the patient lives — including Encino's larger hillside and estate properties. Our team coordinates equipment placement, nursing schedules and supply logistics to fit the home environment, not the other way around.",
},
"fillmore": {
    "county":"Ventura County","subregion":"Santa Clara Valley",
    "neighborhood":"throughout Fillmore's historic downtown neighborhoods and outlying ranches and farms of the Santa Clara Valley",
    "nearby_html": 'nearby <a href="hospice-santa-paula-ca">Santa Paula</a>, <a href="hospice-moorpark-ca">Moorpark</a> and <a href="hospice-ventura-ca">Ventura</a>.',
    "faq6q":"Can hospice care reach agricultural and ranch properties outside of Fillmore proper?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout the rural Santa Clara Valley, including ranches and farms outside Fillmore's city limits. Our team coordinates all logistics — nursing visit schedules, equipment delivery and medication management — to reach patients wherever they live in Ventura County.",
},
"glendale": {
    "county":"Los Angeles County","subregion":"Crescenta Valley",
    "neighborhood":"across Adams Hill, Chevy Chase Canyon, Verdugo Woodlands and Glendale's diverse neighborhoods",
    "nearby_html": 'nearby <a href="hospice-burbank-ca">Burbank</a>, <a href="hospice-pasadena-ca">Pasadena</a> and <a href="hospice-studio-city-ca">Studio City</a>.',
    "faq6q":"How does Eternal Life Hospice support Glendale's culturally diverse families?",
    "faq6a":"Glendale is one of the most culturally diverse cities in Los Angeles County. Our interdisciplinary team is experienced working with families from Armenian, Korean, Hispanic and other cultural backgrounds. We adapt our communication, our care approach and our chaplain support to honor each family's traditions, values and preferences.",
},
"granada-hills": {
    "county":"Los Angeles County","subregion":"North San Fernando Valley",
    "neighborhood":"across Knollwood, the Balboa Boulevard corridor and Granada Hills' established residential streets",
    "nearby_html": 'nearby <a href="hospice-northridge-ca">Northridge</a>, <a href="hospice-west-hills-ca">West Hills</a> and <a href="hospice-canoga-park-ca">Canoga Park</a>.',
    "faq6q":"My parent has lived in their Granada Hills home for 40 years. Can hospice keep them there?",
    "faq6a":"Yes. Hospice is specifically designed to support patients in their own homes — and for many families, that is the most meaningful outcome possible. Our team will provide all of the nursing, medication, equipment and support needed to make care at home safe, comfortable and sustainable for as long as clinically appropriate.",
},
"long-beach": {
    "county":"Los Angeles County","subregion":"South Bay",
    "neighborhood":"across Belmont Shore, Naples Island, Bixby Knolls, Park Estates and Long Beach's many distinct neighborhoods",
    "nearby_html": 'nearby <a href="hospice-torrance-ca">Torrance</a> and <a href="hospice-rancho-palos-verdes-ca">Rancho Palos Verdes</a>.',
    "faq6q":"Long Beach is a large city — does Eternal Life Hospice cover the entire city?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout all neighborhoods of Long Beach — from Belmont Shore to North Long Beach, from Naples Island to Lakewood Village. If you are uncertain whether your specific area is covered, call 805.953.7273 and we will confirm service availability for your address.",
},
"malibu": {
    "county":"Los Angeles County","subregion":"Malibu Coast",
    "neighborhood":"along Pacific Coast Highway from Point Dume to Topanga, in canyon homes above the water and in the Colony",
    "nearby_html": 'nearby <a href="hospice-santa-monica-ca">Santa Monica</a> and <a href="hospice-pacific-palisades-ca">Pacific Palisades</a>.',
    "faq6q":"Malibu is isolated and difficult to access — how does hospice care work in remote canyon homes?",
    "faq6a":"Our team is experienced serving patients in Malibu's canyon properties, beach homes and more remote locations. We plan nursing schedules around road conditions, coordinate equipment delivery directly to the home and ensure that 24/7 on-call nursing access is available for every enrolled patient regardless of how far off Pacific Coast Highway they live.",
},
"moorpark": {
    "county":"Ventura County","subregion":"Arroyo Simi",
    "neighborhood":"throughout Moorpark's residential neighborhoods in the Arroyo Simi Valley",
    "nearby_html": 'nearby <a href="hospice-thousand-oaks-ca">Thousand Oaks</a>, <a href="hospice-simi-valley-ca">Simi Valley</a> and <a href="hospice-newbury-park-ca">Newbury Park</a>.',
    "faq6q":"Moorpark is a newer, growing community — does Eternal Life Hospice serve newer master-planned neighborhoods?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout Moorpark's planned residential communities. We work within HOA guidelines, coordinate with community management where relevant and deliver care to the same standard regardless of whether a patient lives in a newer development or an older neighborhood.",
},
"newbury-park": {
    "county":"Ventura County","subregion":"West Conejo Valley",
    "neighborhood":"throughout Newbury Park's hillside neighborhoods near Wildwood and along the Ventu Park corridor",
    "nearby_html": 'nearby <a href="hospice-thousand-oaks-ca">Thousand Oaks</a>, <a href="hospice-moorpark-ca">Moorpark</a> and <a href="hospice-westlake-village-ca">Westlake Village</a>.',
    "faq6q":"My parent lives near the Wildwood trailhead area of Newbury Park — can hospice reach that address?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout Newbury Park including neighborhoods at the foot of the Santa Monica Mountains near Wildwood and the Ventu Park area. Our team navigates the hillside streets and delivers all care, equipment and medications to wherever the patient lives.",
},
"north-hollywood": {
    "county":"Los Angeles County","subregion":"East San Fernando Valley",
    "neighborhood":"across the NoHo Arts District, Valley Plaza and North Hollywood's diverse residential neighborhoods",
    "nearby_html": 'nearby <a href="hospice-burbank-ca">Burbank</a>, <a href="hospice-studio-city-ca">Studio City</a> and <a href="hospice-toluca-lake-ca">Toluca Lake</a>.',
    "faq6q":"We have a large multigenerational family caregiving at home in North Hollywood. How does hospice work with that?",
    "faq6a":"Hospice is designed to support and reinforce family caregiving, not replace it. Our team works alongside whoever is caring for the patient at home — educating family members, answering questions at all hours, handling the clinical tasks that require professional skill, and ensuring everyone in the household knows what to expect and who to call.",
},
"northridge": {
    "county":"Los Angeles County","subregion":"Central San Fernando Valley",
    "neighborhood":"throughout Northridge's established neighborhoods near CSUN and Porter Ranch-adjacent areas",
    "nearby_html": 'nearby <a href="hospice-canoga-park-ca">Canoga Park</a>, <a href="hospice-granada-hills-ca">Granada Hills</a> and <a href="hospice-west-hills-ca">West Hills</a>.',
    "faq6q":"Does Northridge have many skilled nursing and assisted living options where hospice can be provided?",
    "faq6a":"Yes. Northridge and the surrounding Central San Fernando Valley have a number of skilled nursing facilities and assisted-living communities. Eternal Life Hospice coordinates directly with facility staff to layer hospice care alongside existing services — the patient does not need to move, and care is enhanced, not disrupted.",
},
"ojai": {
    "county":"Ventura County","subregion":"Ojai Valley",
    "neighborhood":"throughout downtown Ojai, Meiners Oaks, Upper Ojai and the surrounding valley, and on ranchos",
    "nearby_html": 'nearby <a href="hospice-ventura-ca">Ventura</a> and <a href="hospice-santa-paula-ca">Santa Paula</a>.',
    "faq6q":"Ojai families often have strong preferences for natural and integrative care. How does Eternal Life Hospice accommodate that?",
    "faq6a":"Eternal Life Hospice provides integrative comfort therapies alongside physician-supervised clinical care — including music therapy, pet companionship, massage and other evidence-aligned modalities. These are offered for comfort and wellbeing, at no additional expense to the family, and they complement the medical plan of care. Ojai families consistently appreciate this whole-person approach.",
},
"oxnard": {
    "county":"Ventura County","subregion":"Oxnard Plain",
    "neighborhood":"across Silver Strand, Hollywood Beach, the Harbor and agricultural communities of the Oxnard Plain",
    "nearby_html": 'nearby <a href="hospice-ventura-ca">Ventura</a>, <a href="hospice-camarillo-ca">Camarillo</a> and <a href="hospice-port-hueneme-ca">Port Hueneme</a>.',
    "faq6q":"Does Eternal Life Hospice serve Spanish-speaking families in Oxnard?",
    "faq6a":"Yes. Oxnard has a large Spanish-speaking population and Eternal Life Hospice is prepared to serve those families. Our team includes staff with Spanish-language capability and we work to ensure that language is never a barrier to accessing or understanding hospice care.",
},
"pasadena": {
    "county":"Los Angeles County","subregion":"San Gabriel Valley",
    "neighborhood":"across Old Town, the Arroyo Seco neighborhoods, Bungalow Heaven and Pasadena's historic residential streets",
    "nearby_html": 'nearby <a href="hospice-arcadia-ca">Arcadia</a>, <a href="hospice-glendale-ca">Glendale</a> and <a href="hospice-alhambra-ca">Alhambra</a>.',
    "faq6q":"Pasadena has historic neighborhoods with older or less accessible homes — can hospice care be delivered there?",
    "faq6a":"Yes. Many of Pasadena's most distinctive homes — Craftsman bungalows, Spanish Revival estates, older multi-story properties — present accessibility considerations that our team navigates regularly. We work with families to adapt care delivery to the specific layout and access needs of each home.",
},
"rancho-palos-verdes": {
    "county":"Los Angeles County","subregion":"Palos Verdes Peninsula",
    "neighborhood":"across Miraleste, Eastview, Seaview and the clifftop communities of the Palos Verdes Peninsula",
    "nearby_html": 'nearby <a href="hospice-torrance-ca">Torrance</a> and <a href="hospice-long-beach-ca">Long Beach</a>.',
    "faq6q":"The Palos Verdes Peninsula has limited access roads. Does that affect hospice care delivery?",
    "faq6a":"No. Our team is experienced navigating the Peninsula's access roads and the routing considerations that come with the geography. Nursing visits, equipment delivery and all other care logistics are planned and executed reliably — access is a logistical challenge our team manages, not one the family needs to worry about.",
},
"reseda": {
    "county":"Los Angeles County","subregion":"West San Fernando Valley",
    "neighborhood":"throughout Reseda's established neighborhoods along the Sherman Way corridor",
    "nearby_html": 'nearby <a href="hospice-canoga-park-ca">Canoga Park</a>, <a href="hospice-northridge-ca">Northridge</a> and <a href="hospice-van-nuys-ca">Van Nuys</a>.',
    "faq6q":"Are there board-and-care homes in Reseda where hospice can be provided?",
    "faq6a":"Yes. Reseda and the surrounding West San Fernando Valley have a number of board-and-care homes. Eternal Life Hospice coordinates directly with board-and-care operators to deliver clinical services, comfort therapies and medication management to residents in these settings — the patient does not need to leave their current home to receive hospice care.",
},
"san-marino": {
    "county":"Los Angeles County","subregion":"San Gabriel Valley",
    "neighborhood":"on San Marino's tree-lined streets and established estates",
    "nearby_html": 'nearby <a href="hospice-arcadia-ca">Arcadia</a>, <a href="hospice-pasadena-ca">Pasadena</a> and <a href="hospice-alhambra-ca">Alhambra</a>.',
    "faq6q":"San Marino families often have complex estates and large homes. How does hospice care work in those settings?",
    "faq6a":"Hospice care adapts to the home, not the other way around. Our team coordinates equipment placement, nursing visit logistics and care delivery around the specific layout and household structure of each San Marino home. We bring the same clinical excellence to every environment.",
},
"santa-clarita": {
    "county":"Los Angeles County","subregion":"Santa Clarita Valley",
    "neighborhood":"across Valencia, Saugus, Newhall and Canyon Country",
    "nearby_html": 'nearby <a href="hospice-westlake-village-ca">Westlake Village</a> and throughout the Santa Clarita Valley.',
    "faq6q":"Santa Clarita is a large, spread-out community. Does Eternal Life Hospice cover all four communities?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout the Santa Clarita Valley — in Valencia, Saugus, Newhall and Canyon Country. We plan nursing visit routes and logistics across the full geography of the Valley and deliver care to enrolled patients wherever they are located within the service area.",
},
"santa-monica": {
    "county":"Los Angeles County","subregion":"Westside",
    "neighborhood":"across the Montana Avenue neighborhood, Ocean Park, Downtown Santa Monica and Sunset Park",
    "nearby_html": 'nearby <a href="hospice-culver-city-ca">Culver City</a>, <a href="hospice-malibu-ca">Malibu</a> and <a href="hospice-beverly-hills-ca">Beverly Hills</a>.',
    "faq6q":"Does Santa Monica have assisted living communities and skilled nursing facilities where hospice can be provided?",
    "faq6a":"Yes. Santa Monica has a number of high-quality assisted living communities and skilled nursing facilities, several within walking distance of the ocean. Eternal Life Hospice coordinates directly with facility staff to layer hospice services alongside existing care — maintaining the patient's existing relationships and daily rhythms.",
},
"santa-paula": {
    "county":"Ventura County","subregion":"Santa Clara River Valley",
    "neighborhood":"throughout Santa Paula's agricultural neighborhoods, historic downtown blocks and rural outskirts along the Santa Clara River",
    "nearby_html": 'nearby <a href="hospice-fillmore-ca">Fillmore</a>, <a href="hospice-ventura-ca">Ventura</a> and <a href="hospice-ojai-ca">Ojai</a>.',
    "faq6q":"Does Eternal Life Hospice serve Spanish-speaking families in Santa Paula?",
    "faq6a":"Yes. Santa Paula has a large Spanish-speaking population and Eternal Life Hospice is prepared to serve those families. We work to ensure that language is never a barrier to understanding or accessing the hospice benefit — from the initial eligibility conversation through the full course of care.",
},
"sherman-oaks": {
    "county":"Los Angeles County","subregion":"Central San Fernando Valley",
    "neighborhood":"across Chandler Estates, Magnolia Woods and Sherman Oaks' established hillside and valley neighborhoods",
    "nearby_html": 'nearby <a href="hospice-encino-ca">Encino</a>, <a href="hospice-studio-city-ca">Studio City</a> and <a href="hospice-van-nuys-ca">Van Nuys</a>.',
    "faq6q":"Does Sherman Oaks have a significant Jewish senior population — does Eternal Life Hospice provide culturally sensitive care?",
    "faq6a":"Yes. Sherman Oaks has a significant Jewish community and Eternal Life Hospice is experienced providing care that honors Jewish traditions, customs and values at end of life. Our chaplain team includes professionals familiar with Jewish end-of-life practices, and we work with families to ensure that care is aligned with their faith and cultural identity.",
},
"simi-valley": {
    "county":"Ventura County","subregion":"East Ventura County",
    "neighborhood":"across the Simi Hills, Wood Ranch, East Simi Valley and surrounding communities",
    "nearby_html": 'nearby <a href="hospice-thousand-oaks-ca">Thousand Oaks</a>, <a href="hospice-moorpark-ca">Moorpark</a> and <a href="hospice-fillmore-ca">Fillmore</a>.',
    "faq6q":"Simi Valley has a significant veteran and law enforcement community. How does Eternal Life Hospice serve those families?",
    "faq6a":"Eternal Life Hospice honors service. We approach the care of veteran and first-responder families with clear communication, reliable scheduling and a team that follows through on commitments. We also help families navigate VA benefit coordination where applicable.",
},
"studio-city": {
    "county":"Los Angeles County","subregion":"Central San Fernando Valley",
    "neighborhood":"across Fryman Estates, Tujunga Village and Studio City's hillside and valley streets",
    "nearby_html": 'nearby <a href="hospice-encino-ca">Encino</a>, <a href="hospice-toluca-lake-ca">Toluca Lake</a> and <a href="hospice-burbank-ca">Burbank</a>.',
    "faq6q":"Studio City has many homes on hillsides above the Valley floor. Does Eternal Life Hospice serve those areas?",
    "faq6a":"Yes. Our team serves patients throughout Studio City's hillside neighborhoods — including Fryman Estates and homes above Mulholland Drive. We plan all logistics around the specific access needs of each location, ensuring reliable nursing visits and supply delivery regardless of elevation or road complexity.",
},
"tarzana": {
    "county":"Los Angeles County","subregion":"Central San Fernando Valley",
    "neighborhood":"across Tarzana's established neighborhoods near Ventura Boulevard and Braemar",
    "nearby_html": 'nearby <a href="hospice-encino-ca">Encino</a>, <a href="hospice-woodland-hills-ca">Woodland Hills</a> and <a href="hospice-sherman-oaks-ca">Sherman Oaks</a>.',
    "faq6q":"Tarzana has a significant Jewish community. Does Eternal Life Hospice provide culturally sensitive care for Jewish families?",
    "faq6a":"Yes. Eternal Life Hospice is experienced providing care that honors Jewish traditions and values at end of life. Our chaplain team includes professionals familiar with Jewish end-of-life practices — including Shabbat and related observances — and we work with families to ensure that care respects their faith and identity at every stage.",
},
"thousand-oaks": {
    "county":"Ventura County","subregion":"Conejo Valley",
    "neighborhood":"across Newbury Park, Lynn Ranch, Lang Ranch, Wildwood and Thousand Oaks' established communities",
    "nearby_html": 'nearby <a href="hospice-westlake-village-ca">Westlake Village</a>, <a href="hospice-newbury-park-ca">Newbury Park</a> and <a href="hospice-camarillo-ca">Camarillo</a>.',
    "faq6q":"Thousand Oaks has many active-adult and senior living communities. Can residents receive hospice in those settings?",
    "faq6a":"Yes. Hospice is fully compatible with active-adult and senior living community life. When a Thousand Oaks resident's health reaches a point where hospice is appropriate, our team coordinates directly with the community's care staff to layer services in — without requiring the resident to leave their home.",
},
"toluca-lake": {
    "county":"Los Angeles County","subregion":"East San Fernando Valley",
    "neighborhood":"along Riverside Drive, around the lake and in the studio-adjacent neighborhoods that define Toluca Lake's distinctive character",
    "nearby_html": 'nearby <a href="hospice-studio-city-ca">Studio City</a>, <a href="hospice-burbank-ca">Burbank</a> and <a href="hospice-north-hollywood-ca">North Hollywood</a>.',
    "faq6q":"Toluca Lake is a quiet neighborhood with a distinctive character. How does Eternal Life Hospice maintain discretion there?",
    "faq6a":"Our team approaches every engagement with the professionalism and discretion that Toluca Lake families expect. Care is delivered by trained clinicians who respect the neighborhood and the household. Communication is channeled through designated family contacts, and all care activities are conducted with minimal disruption to the patient's environment.",
},
"torrance": {
    "county":"Los Angeles County","subregion":"South Bay",
    "neighborhood":"across Old Torrance, Walteria, Riviera Village and Torrance's diverse South Bay neighborhoods",
    "nearby_html": 'nearby <a href="hospice-long-beach-ca">Long Beach</a>, <a href="hospice-rancho-palos-verdes-ca">Rancho Palos Verdes</a> and <a href="hospice-redondo-beach-ca">Redondo Beach</a>.',
    "faq6q":"Torrance has a significant Japanese-American community. Does Eternal Life Hospice provide culturally sensitive care?",
    "faq6a":"Yes. Eternal Life Hospice is experienced providing care that honors Japanese and Japanese-American cultural traditions at end of life. We are attentive to family communication preferences, decision-making structures and any cultural or spiritual practices the family wishes to observe.",
},
"van-nuys": {
    "county":"Los Angeles County","subregion":"Central San Fernando Valley",
    "neighborhood":"throughout Van Nuys' dense residential neighborhoods along Van Nuys Boulevard and Sepulveda Boulevard",
    "nearby_html": 'nearby <a href="hospice-sherman-oaks-ca">Sherman Oaks</a>, <a href="hospice-reseda-ca">Reseda</a> and <a href="hospice-canoga-park-ca">Canoga Park</a>.',
    "faq6q":"Van Nuys has many board-and-care homes. Can residents in those facilities receive hospice?",
    "faq6a":"Yes. Board-and-care homes are one of the most common settings where Eternal Life Hospice provides care in the San Fernando Valley. We work directly with board-and-care operators, coordinate with on-site staff and ensure that each resident receives the full hospice benefit — nursing, medications, equipment, comfort therapies and chaplain support — without disruption to their living arrangement.",
},
"ventura": {
    "county":"Ventura County","subregion":"City of Ventura",
    "neighborhood":"across Midtown, Downtown, the Avenues, Pierpont Bay and the hillside communities above the 101",
    "nearby_html": 'nearby <a href="hospice-oxnard-ca">Oxnard</a>, <a href="hospice-camarillo-ca">Camarillo</a> and <a href="hospice-ojai-ca">Ojai</a>.',
    "faq6q":"Can hospice be provided in Ventura's beach and pier district neighborhoods?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout Ventura's coastal neighborhoods — from Pierpont Bay to the Promenade and the Avenues. Our team coordinates all care logistics for patients in any residential setting near the water, including older homes, beach bungalows and apartments along the Ventura shoreline.",
},
"west-hills": {
    "county":"Los Angeles County","subregion":"West San Fernando Valley",
    "neighborhood":"throughout West Hills' hillside and valley neighborhoods from Fallbrook to the Bell Canyon-adjacent streets",
    "nearby_html": 'nearby <a href="hospice-canoga-park-ca">Canoga Park</a>, <a href="hospice-chatsworth-ca">Chatsworth</a> and <a href="hospice-woodland-hills-ca">Woodland Hills</a>.',
    "faq6q":"West Hills borders some more rural canyon communities. Does Eternal Life Hospice serve the outer areas?",
    "faq6a":"Yes. Eternal Life Hospice serves patients throughout West Hills including neighborhoods near the Santa Susana Mountains and Bell Canyon-adjacent areas. Our team plans all logistics around the specific location of each patient, ensuring reliable nursing visits and supply delivery regardless of how far toward the edge of the Valley the patient lives.",
},
"westlake-village": {
    "county":"Los Angeles County","subregion":"Conejo Valley",
    "neighborhood":"around the lake, in North Ranch, along the Lindero corridor and throughout Westlake Village's established neighborhoods",
    "nearby_html": 'nearby <a href="hospice-thousand-oaks-ca">Thousand Oaks</a>, <a href="hospice-agoura-hills-ca">Agoura Hills</a> and <a href="hospice-newbury-park-ca">Newbury Park</a>.',
    "faq6q":"Westlake Village has several senior living communities. Can residents in those communities receive hospice care?",
    "faq6a":"Yes. Eternal Life Hospice coordinates directly with senior living community staff in Westlake Village to layer hospice services onto existing care — without requiring the resident to leave their home. As the locally based agency, we are particularly well-positioned to serve Conejo Valley senior communities with consistent, timely care.",
},
"woodland-hills": {
    "county":"Los Angeles County","subregion":"West San Fernando Valley",
    "neighborhood":"across Walnut Acres, Mulwood, the Warner Center area and Woodland Hills' distinctive hillside neighborhoods",
    "nearby_html": 'nearby <a href="hospice-west-hills-ca">West Hills</a>, <a href="hospice-tarzana-ca">Tarzana</a> and <a href="hospice-calabasas-ca">Calabasas</a>.',
    "faq6q":"Woodland Hills has several large medical facilities nearby. How does Eternal Life Hospice coordinate with those institutions?",
    "faq6a":"Eternal Life Hospice works directly with discharge planners and care coordinators at West Hills Hospital, Woodland Hills Medical Center and neighboring facilities. Our team participates in care transitions from inpatient settings back to the home and can begin the intake process before a patient is discharged, making the transition seamless.",
},
}

# ── HTML fragments to inject ──────────────────────────────────────────────────

WEBPAGE_SCHEMA_TMPL = """\
  <script type="application/ld+json">{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "@id": "https://eternallifehospice.com/hospice-{slug}-ca#webpage",
  "url": "https://eternallifehospice.com/hospice-{slug}-ca",
  "name": {title_json},
  "description": {desc_json},
  "isPartOf": {{"@id": "https://eternallifehospice.com/#website"}},
  "about": {{"@id": "https://eternallifehospice.com/#organization"}},
  "breadcrumb": {{"@id": "https://eternallifehospice.com/hospice-{slug}-ca#breadcrumb"}},
  "inLanguage": "en-US",
  "dateModified": "2026-07-22"
}}</script>"""

GLANCE_TMPL = """\
<section class="sec wrap" id="at-a-glance">
  <h2>Hospice Care in {city} at a Glance</h2>
  <p class="at-a-glance-summary">Eternal Life Hospice provides physician-supported hospice care to eligible patients and families in {city}, {county}. Care is delivered wherever the patient calls home — in private residences {neighborhood}, in assisted-living communities and skilled nursing facilities throughout the {subregion}. A nurse is on call 24 hours a day, every day, for all enrolled patients and families. Eligibility requires a clinical evaluation and physician certification. Eternal Life Hospice is Medicare-certified, CDPH-licensed and ACHC-accredited. Call 805.953.7273.</p>
</section>"""

RESOURCES_TMPL = """\
<section class="sec wrap">
  <h2>Helpful resources for families in {city}</h2>
  <div class="prov">
    <div><span>&#8227;</span><span><a href="family-guide"><b>Family Guide</b></a> &mdash; eligibility, what to expect and questions to ask when choosing a provider</span></div>
    <div><span>&#8227;</span><span><a href="/resources/first-48-hours"><b>The First 48 Hours</b></a> &mdash; what happens when hospice care begins</span></div>
    <div><span>&#8227;</span><span><a href="/resources/medicare-hospice-benefit"><b>Medicare Hospice Benefit</b></a> &mdash; what Medicare covers and how it works</span></div>
    <div><span>&#8227;</span><span><a href="/resources/what-hospice-covers"><b>What Hospice Covers</b></a> &mdash; services, medications, equipment and support</span></div>
    <div><span>&#8227;</span><span><a href="/resources/how-to-choose-a-hospice"><b>How to Choose a Hospice</b></a> &mdash; questions to ask before enrolling</span></div>
  </div>
</section>"""

NEARBY_NOTE_TMPL = '<p>We also serve families in {nearby_html} <a href="hospice-ventura-and-los-angeles-county-ca">Explore our full service area</a>.</p>'

FAQ6_TMPL = """\
  <details class="faq-item"><summary>{q}</summary><p>{a}</p></details>"""


def extract_city_info(html, slug):
    """Pull city name, title, description from existing HTML."""
    h1 = re.search(r'<h1>([^<]+)</h1>', html)
    city = h1.group(1).replace("Hospice Care in ", "").strip() if h1 else slug.replace("-", " ").title()
    title = re.search(r'<title>([^<]+)</title>', html)
    title_str = title.group(1).strip() if title else ""
    desc = re.search(r'name="description"\s+content="([^"]+)"', html)
    desc_str = desc.group(1).strip() if desc else ""
    return city, title_str, desc_str


def patch_page(slug, html):
    meta = CITY_META.get(slug)
    if not meta:
        print(f"  SKIP {slug} — no metadata")
        return html

    city, title_str, desc_str = extract_city_info(html, slug)
    county    = meta["county"]
    subregion = meta["subregion"]
    neighborhood = meta["neighborhood"]

    # ── 1. Add WebPage schema if missing ─────────────────────────────
    if '"WebPage"' not in html and "#webpage" not in html:
        webpage_block = WEBPAGE_SCHEMA_TMPL.format(
            slug=slug,
            title_json=json.dumps(title_str),
            desc_json=json.dumps(desc_str)
        )
        # Insert after the last </script> before </head>
        html = re.sub(
            r'((?:<script type="application/ld\+json">.*?</script>\s*)+)(\s*<script async)',
            lambda m: m.group(1) + webpage_block + "\n" + m.group(2),
            html, count=1, flags=re.DOTALL
        )

    # ── 2. Add At-a-Glance section if missing ─────────────────────────
    if 'id="at-a-glance"' not in html and 'at-a-glance-summary' not in html:
        glance_block = GLANCE_TMPL.format(
            city=city, county=county, subregion=subregion, neighborhood=neighborhood
        )
        # Insert before the first <section class="sec wrap"> after the breadcrumb nav
        html = re.sub(
            r'(</nav>\s*\n)(\s*<section class="sec wrap")',
            lambda m: m.group(1) + "\n" + glance_block + "\n\n" + m.group(2),
            html, count=1
        )

    # ── 3. Add resources section with how-to-choose if missing ───────
    if 'how-to-choose-a-hospice' not in html:
        resources_block = RESOURCES_TMPL.format(city=city)
        # Insert before the "For physicians" section or before the FAQs
        inserted = False
        for pattern in [
            r'(<section class="sec wrap">\s*<h2>For physicians)',
            r'(<section class="sec wrap lfaq">)',
        ]:
            if re.search(pattern, html):
                html = re.sub(pattern, resources_block + "\n" + r'\1', html, count=1)
                inserted = True
                break
        if not inserted:
            # fallback: insert before footer
            html = html.replace('<footer id="site-footer">', resources_block + '\n<footer id="site-footer">', 1)

    # ── 4. Add 6th FAQ if only 5 exist ───────────────────────────────
    faq_count = len(re.findall(r'<details class="faq-item"', html))
    if faq_count < 6:
        faq6 = FAQ6_TMPL.format(q=meta["faq6q"], a=meta["faq6a"])
        # Append before </section> after the last faq-item
        html = re.sub(
            r'((?:<details class="faq-item">.*?</details>\s*)+)(</section>)',
            lambda m: m.group(1) + faq6 + "\n" + m.group(2),
            html, count=1, flags=re.DOTALL
        )

    # ── 5. Add nearby-city cross-link note in intro section ──────────
    nearby_html = meta.get("nearby_html", "")
    if nearby_html and nearby_html[:20] not in html:
        nearby_note = NEARBY_NOTE_TMPL.format(nearby_html=nearby_html)
        # Insert after first <p> in the intro section (second sec wrap section)
        sections = list(re.finditer(r'<section class="sec wrap">', html))
        # find the intro section (skip at-a-glance which is first now)
        intro_idx = None
        for m in sections:
            chunk = html[m.start():m.start()+200]
            if 'at-a-glance' not in chunk:
                intro_idx = m.start()
                break
        if intro_idx is not None:
            # find first </p> in this section and append the note after it
            p_end = html.find('</p>', intro_idx)
            if p_end != -1:
                html = html[:p_end+4] + "\n  " + nearby_note + html[p_end+4:]

    return html


def main():
    slugs = list(CITY_META.keys())
    ok, skipped = 0, 0
    for slug in slugs:
        path = os.path.join(OUT_DIR, f"hospice-{slug}-ca.html")
        if not os.path.exists(path):
            print(f"  MISSING {path}")
            skipped += 1
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()
        patched = patch_page(slug, html)
        if patched != html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(patched)
            print(f"  ✓ patched {slug}")
            ok += 1
        else:
            print(f"  ~ unchanged {slug}")

    print(f"\nDone: {ok} patched, {skipped} missing")


if __name__ == "__main__":
    main()
