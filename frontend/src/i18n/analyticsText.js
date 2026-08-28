const TURKISH_EXACT_TEXT = new Map([
  ['Interpretation is limited by unavailable context.', 'Yorumlama, mevcut olmayan bağlam nedeniyle sınırlıdır.'],
  ['Competitor pricing may affect interpretation of Revenue movements.', 'Rakip fiyatlandırması, Revenue hareketlerinin yorumlanmasını etkileyebilir.'],
  ['AverageOrderValue growth does not establish that individual selling prices increased.', 'AverageOrderValue artışı, tekil satış fiyatlarının arttığını kanıtlamaz.'],
  ['Explicit pricing policy changes are unavailable.', 'Açık fiyatlandırma politikası değişikliklerine ilişkin bilgi mevcut değildir.'],
  ['A failed consistency reconciliation blocks narration.', 'Başarısız bir tutarlılık uzlaştırması anlatımı engeller.'],
  ['A data contradiction blocks narration.', 'Bir veri çelişkisi anlatımı engeller.'],
  ['A semantic contradiction blocks narration.', 'Anlamsal bir çelişki anlatımı engeller.'],
  ['An insight contradiction requires review and blocks narration.', 'Bir içgörü çelişkisi inceleme gerektirir ve anlatımı engeller.'],
  ['Counter evidence is present and requires qualification.', 'Karşı kanıt mevcuttur ve nitelendirme gerektirir.'],
  ['High outlier dependency requires review and qualification.', 'Yüksek aykırı değer bağımlılığı inceleme ve nitelendirme gerektirir.'],
  ['Low outlier dependency requires qualification.', 'Düşük aykırı değer bağımlılığı nitelendirme gerektirir.'],
  ['Medium outlier dependency requires qualification.', 'Orta düzey aykırı değer bağımlılığı nitelendirme gerektirir.'],
  ['High one-off risk requires review and qualification.', 'Yüksek tek seferlik etki riski inceleme ve nitelendirme gerektirir.'],
  ['Low one-off risk requires qualification.', 'Düşük tek seferlik etki riski nitelendirme gerektirir.'],
  ['Medium one-off risk requires qualification.', 'Orta düzey tek seferlik etki riski nitelendirme gerektirir.'],
  ['The insight remains story eligible with qualification.', 'İçgörü, nitelendirme ile hikâyeye uygun olmaya devam eder.'],
  ['No integrity findings require qualification.', 'Hiçbir bütünlük bulgusu nitelendirme gerektirmiyor.'],
  ['No material outlier was found in the trend period.', 'Eğilim döneminde önemli bir aykırı değer bulunmadı.'],
  ['CO_MOVES_WITH is association evidence and does not establish causality on its own.', 'Birlikte hareket ilişkisi, ilişki kanıtıdır ve tek başına nedensellik oluşturmaz.'],
  ['Causality is established by explicitly supplied evidence.', 'Nedensellik, açıkça sağlanan kanıtla oluşturulmuştur.'],
  ['Available evidence does not establish causality for this claim.', 'Mevcut kanıt bu iddia için nedensellik oluşturmamaktadır.'],
  ['Linear trend slope', 'Doğrusal eğilim eğimi'],
  ['Directional persistence ratio', 'Yönsel süreklilik oranı'],
  ['Monotonic movement', 'Tekdüze hareket'],
  ['Periods analyzed', 'İncelenen dönemler'],
  ['Segment previous period value', 'Segment önceki dönem değeri'],
  ['Segment current period value', 'Segment güncel dönem değeri'],
  ['Segment absolute change', 'Segment mutlak değişimi'],
  ['Total absolute change', 'Toplam mutlak değişim'],
  ['Contribution share', 'Katkı payı'],
  ['Contributor role', 'Katkı rolü'],
  ['Subject previous period value', 'İncelenen önceki dönem değeri'],
  ['Subject current period value', 'İncelenen güncel dönem değeri'],
  ['Subject percentage change', 'İncelenen yüzde değişimi'],
  ['Comparison previous period value', 'Karşılaştırılan önceki dönem değeri'],
  ['Comparison current period value', 'Karşılaştırılan güncel dönem değeri'],
  ['Comparison percentage change', 'Karşılaştırılan yüzde değişimi'],
  ['Percentage-point difference', 'Yüzde puan farkı'],
  ['Comparison result', 'Karşılaştırma sonucu'],
  ['Previous period value', 'Önceki dönem değeri'],
  ['Current period value', 'Güncel dönem değeri'],
  ['Absolute change', 'Mutlak değişim'],
  ['Percentage change', 'Yüzde değişim'],
  ['Observed period value', 'Gözlenen dönem değeri'],
  ['Historical first quartile', 'Tarihsel birinci çeyrek'],
  ['Historical third quartile', 'Tarihsel üçüncü çeyrek'],
  ['Lower anomaly bound', 'Alt anomali sınırı'],
  ['Upper anomaly bound', 'Üst anomali sınırı'],
  ['Previous ReturnRate', 'Önceki ReturnRate'],
  ['Current ReturnRate', 'Güncel ReturnRate'],
  ['Relative percentage change', 'Göreli yüzde değişim'],
  ['Percentage-point change', 'Yüzde puan değişimi'],
])

const CONTEXT_CODES = {
  INSIGHT_OBSERVED: { en: 'Insight Observed', tr: 'İçgörü Gözlemlendi' },
  ASSOCIATION_PRESENT: { en: 'Association Present', tr: 'İlişki Mevcut' },
  CAUSALITY_NOT_ESTABLISHED: { en: 'Causality Not Established', tr: 'Nedensellik Kanıtlanmadı' },
  COMPETITORPRICE_UNAVAILABLE: { en: 'Competitor Price Unavailable', tr: 'Rakip Fiyatı Mevcut Değil' },
  UNITPRICE_UNAVAILABLE: { en: 'Unit Price Unavailable', tr: 'Birim Fiyat Mevcut Değil' },
  PRICINGCHANGE_UNAVAILABLE: { en: 'Pricing Change Unavailable', tr: 'Fiyatlandırma Değişimi Mevcut Değil' },
}

const TURKISH_CONTROLLED_TOKENS = new Map([
  ['HIGHER_IS_BETTER', 'yüksek değer daha iyi'],
  ['LOWER_IS_BETTER', 'düşük değer daha iyi'],
  ['CO_MOVES_WITH', 'birlikte hareket'],
  ['COUNTER_SIGNAL', 'karşı sinyal'],
  ['CONTRIBUTES_TO', 'katkı ilişkisi'],
  ['RELATED_ANOMALY', 'ilişkili anomali'],
  ['DRILLDOWN_OF', 'alt kırılım'],
  ['UP', 'yukarı'],
  ['DOWN', 'aşağı'],
  ['STABLE', 'sabit'],
  ['HIGH', 'yüksek'],
  ['MEDIUM', 'orta'],
  ['LOW', 'düşük'],
  ['CompetitorPrice', 'Rakip Fiyatı'],
  ['UnitPrice', 'Birim Fiyat'],
  ['PricingChange', 'Fiyatlandırma Değişimi'],
])

const localizeControlledTokens = (text) => {
  let localized = text
  for (const [source, target] of TURKISH_CONTROLLED_TOKENS) {
    localized = localized.replaceAll(source, target)
  }
  return localized
}

const TURKISH_TEMPLATES = [
  [/^The insight for (.+) is an observed analytical finding\.$/, ([, metric]) => `${metric} içgörüsü gözlemlenmiş bir analitik bulgudur.`],
  [/^Association evidence is present between (.+) and (.+)\.$/, ([, source, target]) => `${source} ile ${target} arasında ilişki kanıtı mevcuttur.`],
  [/^Causality between (.+) and (.+) is not established\.$/, ([, source, target]) => `${source} ile ${target} arasında nedensellik kanıtlanmamıştır.`],
  [/^(.+) is unavailable as contextual information\.$/, ([, field]) => `${field}, bağlamsal bilgi olarak mevcut değildir.`],
  [/^Event period (\S+) moved from baseline (\S+) to (\S+); next period (\S+) was (\S+), producing reversion ratio (\S+)\.$/, ([, eventPeriod, baseline, eventValue, nextPeriod, nextValue, ratio]) => `${eventPeriod} olay döneminde değer ${baseline} baz seviyesinden ${eventValue} seviyesine çıktı; sonraki dönem olan ${nextPeriod} değeri ${nextValue} oldu ve geri dönüş oranı ${ratio} olarak kaydedildi.`],
  [/^Event period (\S+) does not deviate from the historical baseline, so no one-off effect was found\.$/, ([, period]) => `${period} olay dönemi tarihsel baz seviyeden sapmadığı için tek seferlik etki bulunmadı.`],
  [/^Removing dominant outlier period (\S+) changed the trend slope from (\S+) to (\S+); slope magnitude reduction was (\S+) and adjusted persistence was (\S+)\.$/, ([, period, original, adjusted, reduction, persistence]) => `Baskın aykırı dönem ${period} çıkarıldığında eğilim eğimi ${original} değerinden ${adjusted} değerine değişti; eğim büyüklüğü azalması ${reduction}, düzeltilmiş süreklilik ise ${persistence} oldu.`],
  [/^Insight (.+) reports direction (\S+), opposing primary insight (.+) direction (\S+) for the same claim\.$/, ([, relatedId, relatedDirection, primaryId, primaryDirection]) => `${relatedId} içgörüsü ${relatedDirection} yönünü bildiriyor; bu, aynı iddia için ${primaryId} birincil içgörüsünün ${primaryDirection} yönüne karşıttır.`],
  [/^Insight (.+) reports direction (\S+) but percentageChange is (.+)\.$/, ([, id, direction, value]) => `${id} içgörüsü ${direction} yönünü bildiriyor ancak percentageChange değeri ${value}.`],
  [/^(.+) is not evaluated as causal by this causality guard rule\.$/, ([, type]) => `${type}, bu nedensellik kontrolü kuralı tarafından nedensel olarak değerlendirilmez.`],
  [/^Same metric: (.+)$/, ([, metric]) => `Aynı metrik: ${metric}`],
  [/^Anomaly current period (.+) matches company-level change current period$/, ([, period]) => `Anomalinin güncel dönemi ${period}, şirket düzeyindeki değişimin güncel dönemiyle eşleşiyor`],
  [/^Segment anomaly direction (.+) is compatible with company-level change direction (.+)$/, ([, anomalyDirection, changeDirection]) => `Segment anomalisi yönü ${anomalyDirection}, şirket düzeyindeki değişim yönü ${changeDirection} ile uyumludur`],
  [/^Same comparison period: (.+) to (.+)$/, ([, previous, current]) => `Aynı karşılaştırma dönemi: ${previous} - ${current}`],
  [/^Configured (.+) metric pair: (.+) -> (.+)$/, ([, type, source, target]) => `Yapılandırılmış ${type} metrik çifti: ${source} -> ${target}`],
  [/^(.+) and (.+) both moved (.+)$/, ([, source, target, direction]) => `${source} ve ${target} birlikte ${direction} yönünde hareket etti`],
  [/^(.+) moved (.+) while (.+) moved (.+)$/, ([, source, sourceDirection, target, targetDirection]) => `${source} ${sourceDirection} yönünde hareket ederken ${target} ${targetDirection} yönünde hareket etti`],
  [/^Contribution totals match the company-level (.+) change$/, ([, metric]) => `Katkı toplamları şirket düzeyindeki ${metric} değişimiyle eşleşiyor`],
  [/^(.+) contributed (.+) of the total (.+) change$/, ([, segment, share, metric]) => `${segment}, toplam ${metric} değişiminin ${share} bölümüne katkıda bulundu`],
  [/^(.+) has configured business priority (.+)\.$/, ([, metric, priority]) => `${metric} için yapılandırılmış iş önceliği ${priority}.`],
  [/^(.+) moved (.+) and is configured as (.+)\.$/, ([, metric, direction, directionality]) => `${metric} ${direction} yönünde hareket etti ve ${directionality} olarak yapılandırıldı.`],
  [/^Relationship context supported by (.+)\.$/, ([, types]) => `İlişki bağlamı ${types} tarafından destekleniyor.`],
  [/^Analytical importance: (.+)\.$/, ([, value]) => `Analitik önem: ${value}.`],
  [/^Business relevance: (.+)\.$/, ([, value]) => `İş açısından önem: ${value}.`],
  [/^Confidence: (.+)\.$/, ([, value]) => `Güven: ${value}.`],
  [/^Priority score (.+) maps to (.+)\.$/, ([, score, level]) => `Öncelik puanı ${score}, ${level} düzeyine karşılık geliyor.`],
  [/^Previous period (.+): whole total (.+), summed (.+) total (.+), difference (.+)\. Current period (.+): whole total (.+), summed (.+) total (.+), difference (.+)\.$/, ([, previousPeriod, previousWhole, dimension, previousGrouped, previousDifference, currentPeriod, currentWhole, currentDimension, currentGrouped, currentDifference]) => `Önceki dönem ${previousPeriod}: genel toplam ${previousWhole}, toplanmış ${dimension} toplamı ${previousGrouped}, fark ${previousDifference}. Güncel dönem ${currentPeriod}: genel toplam ${currentWhole}, toplanmış ${currentDimension} toplamı ${currentGrouped}, fark ${currentDifference}.`],
  [/^Contribution total reconciliation: previous: expected (.+), actual (.+), difference (.+); current: expected (.+), actual (.+), difference (.+); absolute change: expected (.+), actual (.+), difference (.+)\.$/, ([, previousExpected, previousActual, previousDifference, currentExpected, currentActual, currentDifference, changeExpected, changeActual, changeDifference]) => `Katkı toplamı uzlaştırması: önceki değer için beklenen ${previousExpected}, gerçekleşen ${previousActual}, fark ${previousDifference}; güncel değer için beklenen ${currentExpected}, gerçekleşen ${currentActual}, fark ${currentDifference}; mutlak değişim için beklenen ${changeExpected}, gerçekleşen ${changeActual}, fark ${changeDifference}.`],
]

export function localizeAnalyticsText(text, language) {
  if (typeof text !== 'string' || language !== 'tr') return text
  const exact = TURKISH_EXACT_TEXT.get(text)
  if (exact) return localizeControlledTokens(exact)
  for (const [pattern, render] of TURKISH_TEMPLATES) {
    const match = text.match(pattern)
    if (match) return localizeControlledTokens(render(match))
  }
  return text
}

export function localizeAnalyticsCode(code, language) {
  if (typeof code !== 'string') return code
  return CONTEXT_CODES[code]?.[language === 'tr' ? 'tr' : 'en'] || code
}
