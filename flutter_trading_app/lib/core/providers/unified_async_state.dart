import 'package:flutter_riverpod/flutter_riverpod.dart';

enum LoadingStatus { initial, loading, loaded, error, empty }

class LoadingState<T> {
  final LoadingStatus status;
  final T? data;
  final String? error;
  final bool isRefreshing;

  const LoadingState({
    this.status = LoadingStatus.initial,
    this.data,
    this.error,
    this.isRefreshing = false,
  });

  LoadingState<T> copyWith({
    LoadingStatus? status,
    T? data,
    String? error,
    bool? isRefreshing,
  }) =>
      LoadingState(
        status: status ?? this.status,
        data: data ?? this.data,
        error: error,
        isRefreshing: isRefreshing ?? this.isRefreshing,
      );

  bool get isLoading => status == LoadingStatus.loading;
  bool get isLoaded => status == LoadingStatus.loaded;
  bool get isEmpty => status == LoadingStatus.empty;
  bool get isError => status == LoadingStatus.error;
  bool get isInitial => status == LoadingStatus.initial;
  bool get enabled => status == LoadingStatus.loaded || status == LoadingStatus.initial;

  R when<R>({
    required R Function() loading,
    required R Function(T data) data,
    required R Function(String error, StackTrace? stackTrace) error,
    R Function()? empty,
  }) {
    if (isLoading) return loading();
    if (status == LoadingStatus.error) return error(this.error ?? 'Unknown error', null);
    if (isEmpty && empty != null) return empty();
    if (this.data != null) return data(this.data as T);
    return loading();
  }

  R maybeWhen<R>({
    required R Function() orElse,
    R Function()? loading,
    R Function(T data)? data,
    R Function(String error, StackTrace? stackTrace)? error,
    R Function()? empty,
  }) {
    if (isLoading && loading != null) return loading();
    if (status == LoadingStatus.error && error != null) return error(this.error ?? 'Unknown error', null);
    if (isEmpty && empty != null) return empty();
    if (this.data != null && data != null) return data(this.data as T);
    return orElse();
  }
}

class LoadingNotifier<T> extends StateNotifier<LoadingState<T>> {
  LoadingNotifier() : super(const LoadingState());

  void setLoading() => state = const LoadingState(status: LoadingStatus.loading);

  void setLoaded(T data) =>
      state = LoadingState(status: LoadingStatus.loaded, data: data);

  void setError(String message) =>
      state = LoadingState(status: LoadingStatus.error, error: message);

  void setEmpty() => state = const LoadingState(status: LoadingStatus.empty);

  void setRefreshing(T data) => state = LoadingState(
    status: LoadingStatus.loaded,
    data: data,
    isRefreshing: true,
  );

  Future<void> load(Future<T> Function() fetch) async {
    setLoading();
    try {
      final result = await fetch();
      if (result == null) {
        setEmpty();
      } else {
        setLoaded(result);
      }
    } catch (e) {
      setError(e.toString());
    }
  }

  Future<void> refresh(Future<T> Function() fetch, {T? currentData}) async {
    if (currentData != null) {
      setRefreshing(currentData);
    }
    try {
      final result = await fetch();
      setLoaded(result);
    } catch (e) {
      if (currentData == null) {
        setError(e.toString());
      }
    }
  }
}

enum ScreenState { loading, loaded, error, empty }

class UnifiedAsyncState<T> {
  final LoadingStatus status;
  final T? data;
  final String? error;
  final bool isRefreshing;

  const UnifiedAsyncState._({
    this.status = LoadingStatus.initial,
    this.data,
    this.error,
    this.isRefreshing = false,
  });

  factory UnifiedAsyncState.initial() =>
      const UnifiedAsyncState._(status: LoadingStatus.initial);

  factory UnifiedAsyncState.loading() =>
      const UnifiedAsyncState._(status: LoadingStatus.loading);

  factory UnifiedAsyncState.loaded(T data) => UnifiedAsyncState._(
        status: LoadingStatus.loaded,
        data: data,
      );

  factory UnifiedAsyncState.error(String message) => UnifiedAsyncState._(
        status: LoadingStatus.error,
        error: message,
      );

  factory UnifiedAsyncState.empty() =>
      const UnifiedAsyncState._(status: LoadingStatus.empty);

  factory UnifiedAsyncState.refreshing(T data) => UnifiedAsyncState._(
        status: LoadingStatus.loaded,
        data: data,
        isRefreshing: true,
      );

  bool get isLoading => status == LoadingStatus.loading;
  bool get isLoaded => status == LoadingStatus.loaded;
  bool get isEmpty => status == LoadingStatus.empty;
  bool get isError => status == LoadingStatus.error;
  bool get isInitial => status == LoadingStatus.initial;
  bool get isCurrentlyRefreshing => isRefreshing;

  ScreenState get screenState {
    if (isLoading) return ScreenState.loading;
    if (isError) return ScreenState.error;
    if (isEmpty) return ScreenState.empty;
    return ScreenState.loaded;
  }
}

class UnifiedNotifier<T> extends StateNotifier<UnifiedAsyncState<T>> {
  UnifiedNotifier() : super(UnifiedAsyncState<T>.initial());

  void setLoading() => state = UnifiedAsyncState<T>.loading();
  void setLoaded(T data) => state = UnifiedAsyncState<T>.loaded(data);
  void setError(String message) => state = UnifiedAsyncState<T>.error(message);
  void setEmpty() => state = UnifiedAsyncState<T>.empty();
  void setRefreshing(T data) => state = UnifiedAsyncState<T>.refreshing(data);

  Future<void> run(Future<T> Function() future) async {
    setLoading();
    try {
      final result = await future();
      if (result == null || (result is List && result.isEmpty)) {
        setEmpty();
      } else {
        setLoaded(result);
      }
    } catch (e) {
      setError(e.toString());
    }
  }

  Future<void> runWithCache(T? cached, Future<T> Function() future) async {
    if (cached != null) setLoaded(cached);
    if (cached != null) setRefreshing(cached);
    try {
      final result = await future();
      setLoaded(result);
    } catch (e) {
      if (cached == null) {
        setError(e.toString());
      }
    }
  }
}
