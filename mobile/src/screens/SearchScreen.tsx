/**
 * Search screen — main entry point for lyric fragment search.
 */

import React, { useState, useRef } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Keyboard,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';
import { Ionicons } from '@expo/vector-icons';

import { useSearch } from '../hooks/useSearch';
import { ResultCard } from '../components/ResultCard';
import { LanguageChip } from '../components/LanguageChip';
import { ErrorBanner } from '../components/ErrorBanner';
import { COLORS } from '../constants/colors';

const HINTS = [
  'comme un petit coeur qui bat',
  'la la la',
  'somewhere over the rainbow',
  'على بعض الكلمات',
  'todo lo que tengo soy yo',
];

export default function SearchScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<any>();
  const inputRef = useRef<TextInput>(null);

  const [query, setQuery] = useState('');
  const [useTranslation_, setUseTranslation] = useState(false);
  const [yearMin, setYearMin] = useState<number | undefined>();
  const [yearMax, setYearMax] = useState<number | undefined>();
  const [filterLang, setFilterLang] = useState<string | undefined>();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { search, results, isLoading, error, detectedLang, queryId } = useSearch();

  const handleSearch = async () => {
    if (!query.trim()) return;
    Keyboard.dismiss();
    const res = await search({
      query_text: query.trim(),
      top_k: 10,
      use_translation: useTranslation_,
      filter_year_min: yearMin,
      filter_year_max: yearMax,
      filter_language: filterLang,
    });
    if (res && res.results.length > 0) {
      navigation.navigate('Results', { results: res.results, query, queryId: res.query_id });
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.scroll}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.logo}>🎵 LyricFinder</Text>
          <Text style={styles.sub}>{t('search.subtitle')}</Text>
        </View>

        {/* Search input */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={COLORS.textSecondary} />
          <TextInput
            ref={inputRef}
            style={styles.input}
            placeholder={t('search.placeholder')}
            placeholderTextColor={COLORS.textTertiary}
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={handleSearch}
            returnKeyType="search"
            autoCorrect={false}
            autoCapitalize="none"
            multiline={false}
            accessibilityLabel={t('search.inputLabel')}
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')} accessibilityLabel="Clear">
              <Ionicons name="close-circle" size={18} color={COLORS.textSecondary} />
            </TouchableOpacity>
          )}
          <TouchableOpacity
            onPress={() => {/* Voice search — expo-speech-recognition */}}
            accessibilityLabel={t('search.voiceSearch')}
          >
            <Ionicons name="mic-outline" size={18} color={COLORS.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* Language chips */}
        <View style={styles.chips}>
          <LanguageChip
            label={detectedLang ? `🌐 ${detectedLang.toUpperCase()} detected` : t('search.autoDetect')}
            active
          />
          <LanguageChip
            label={t('search.translateQuery')}
            active={useTranslation_}
            onPress={() => setUseTranslation(v => !v)}
          />
        </View>

        {/* Advanced filters toggle */}
        <TouchableOpacity
          style={styles.advancedToggle}
          onPress={() => setShowAdvanced(v => !v)}
        >
          <Text style={styles.advancedToggleText}>
            {t('search.advanced')} {showAdvanced ? '▲' : '▼'}
          </Text>
        </TouchableOpacity>

        {showAdvanced && (
          <View style={styles.advancedPanel}>
            <Text style={styles.advancedLabel}>{t('search.yearRange')}</Text>
            <View style={styles.row}>
              <TextInput
                style={[styles.advancedInput, { flex: 1, marginRight: 8 }]}
                placeholder="From"
                keyboardType="number-pad"
                onChangeText={v => setYearMin(v ? parseInt(v) : undefined)}
              />
              <TextInput
                style={[styles.advancedInput, { flex: 1 }]}
                placeholder="To"
                keyboardType="number-pad"
                onChangeText={v => setYearMax(v ? parseInt(v) : undefined)}
              />
            </View>
          </View>
        )}

        {/* Hints */}
        <Text style={styles.hintsLabel}>{t('search.tryFragment')}</Text>
        <View style={styles.hintsRow}>
          {HINTS.map(hint => (
            <TouchableOpacity
              key={hint}
              style={styles.hint}
              onPress={() => { setQuery(hint); inputRef.current?.focus(); }}
            >
              <Text style={styles.hintText} numberOfLines={1}>{hint}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Search button */}
        <TouchableOpacity
          style={[styles.searchBtn, !query.trim() && styles.searchBtnDisabled]}
          onPress={handleSearch}
          disabled={!query.trim() || isLoading}
          accessibilityRole="button"
          accessibilityLabel={t('search.button')}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="search" size={16} color="#fff" />
              <Text style={styles.searchBtnText}>{t('search.button')}</Text>
            </>
          )}
        </TouchableOpacity>

        {error && <ErrorBanner message={error} />}

        {/* Inline results (if navigating in-place) */}
        {results?.map(r => (
          <ResultCard
            key={r.track_id}
            result={r}
            queryId={queryId ?? ''}
            onPress={() => navigation.navigate('Track', { trackId: r.track_id })}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  header: { marginBottom: 20 },
  logo: { fontSize: 22, fontWeight: '600', color: '#1a1a1a' },
  sub: { fontSize: 13, color: '#666', marginTop: 4 },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#f5f5f4',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 0.5,
    borderColor: '#d4d4d0',
  },
  input: { flex: 1, fontSize: 14, color: '#1a1a1a' },
  chips: { flexDirection: 'row', gap: 8, marginTop: 10, flexWrap: 'wrap' },
  advancedToggle: { marginTop: 12 },
  advancedToggleText: { fontSize: 12, color: '#6366f1' },
  advancedPanel: { marginTop: 8 },
  advancedLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  advancedInput: {
    borderWidth: 0.5,
    borderColor: '#d4d4d0',
    borderRadius: 8,
    padding: 8,
    fontSize: 13,
    color: '#1a1a1a',
    backgroundColor: '#f9f9f8',
  },
  row: { flexDirection: 'row' },
  hintsLabel: { fontSize: 12, color: '#888', marginTop: 16, marginBottom: 6 },
  hintsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  hint: {
    backgroundColor: '#f5f5f4',
    borderWidth: 0.5,
    borderColor: '#d4d4d0',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 5,
    maxWidth: 200,
  },
  hintText: { fontSize: 12, color: '#555' },
  searchBtn: {
    marginTop: 20,
    backgroundColor: '#6366f1',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  searchBtnDisabled: { opacity: 0.5 },
  searchBtnText: { color: '#fff', fontSize: 15, fontWeight: '500' },
});
